import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union, Dict, Callable
from urllib.parse import urlparse

from utils import keys_mapping,read_with_retry,screenshot_with_retry,_safe_eval
from utils import (
    safe_click_at, safe_key, safe_scroll,
    switch_to_page, safe_go_back, safe_go_forward
)
from playwright.async_api import Page, BrowserContext, Keyboard, Mouse, Error as PWError
from human_pause import PAUSE_ON_CHALLENGE, pause_if_captcha_then_screenshot,detect_captcha_quick

_CAP_KWS = ("captcha","hcaptcha","recaptcha","cloudflare","cf-chl","are you a robot","human verification","challenge","verify")

def _looks_like_captcha(text: str | None) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in _CAP_KWS)

   
async def _default_cli_waiter_async(reason: str = ""):
    print(f"[HITL] Detected: {reason or 'human intervention required'}")
    # input("After completing in the browser, press Enter to continue...")
    await asyncio.to_thread(input, "After completing in the browser, press Enter to continue...")
    
class HITLPause(Exception):
    """Used to signal that human input is required to proceed."""
    pass

def _kind(v):
    # Prefer Enum.value when available, else use v
    val = getattr(v, "value", v)
    if isinstance(val, str):
        return val.strip().lower()
    return str(val).strip().lower()
    
# async def _dom_signature(page):
#     # URL + 文本长度，足够轻量也能反映“页面是否变了”
#     try:
#         return await page.evaluate("() => location.href + '|' + (document.body?.innerText?.length||0)")
#     except Exception:
#         return page.url + "|?"

# async def _maybe_scroll_into_view(page, x, y):
#     vp = await page.evaluate("() => ({w: innerWidth, h: innerHeight, sx: scrollX, sy: scrollY})")
#     if not (0 <= x < vp["w"] and 0 <= y < vp["h"]):
#         await page.evaluate(
#             "([x,y,sy]) => window.scrollTo({top: Math.max(0, y + sy - innerHeight/2), behavior:'instant'})",
#             [x, y, vp["sy"]],
#         )

# async def _probe_point(page, x, y):
#     js = """
#     ([x,y]) => {
#     const el = document.elementFromPoint(x,y);
#     if (!el) return null;
#     const cs = getComputedStyle(el);
#     const visible = cs && cs.visibility!=='hidden' && cs.display!=='none' && parseFloat(cs.opacity||'1')>0.01;
#     const pe = cs && cs.pointerEvents!=='none';
#     const a = el.closest('a[href], [role="link"][href]');
#     const submit = el.closest('button[type="submit"], input[type="submit"]');
#     const newTab = a && (a.target==='_blank' || a.rel?.includes('noopener'));
#     return { visible, pe, navLikely: !!(a||submit), popupLikely: !!newTab };
#     }
#     """
#     return await page.evaluate(js, [x, y])

# async def safe_click_at(page, x: int, y: int, nav_timeout=10000):
#     # 记录点击前的页面特征
#     before = await _dom_signature(page)

#     # 仅在必要时把目标滚进视口
#     await _maybe_scroll_into_view(page, x, y)

#     # 目标探测（避免点空/被遮挡）
#     info = await _probe_point(page, x, y)
#     if not info or not (info["visible"] and info["pe"]):
#         # 轻等一会儿再测一次，给布局个稳定机会
#         await asyncio.sleep(0.12)
#         info = await _probe_point(page, x, y)
#         if not info or not (info["visible"] and info["pe"]):
#             return False  # 不盲点，让上层决定是否重试/改策略

#     try:
#         # 可能弹新页
#         if info.get("popupLikely"):
#             async with page.expect_popup() as p:
#                 await page.mouse.click(int(x), int(y))
#             newp = await p.value
#             await newp.wait_for_load_state("domcontentloaded")
#             # 如果你有 BrowserAgent，记得把 self.page = newp
#             return True

#         # 可能发生导航（当前页）
#         if info.get("navLikely"):
#             async with page.expect_navigation(wait_until="domcontentloaded", timeout=nav_timeout):
#                 await page.mouse.click(int(x), int(y))
#             return True

#         # 非导航点击：执行 + 微沉淀
#         await page.mouse.click(int(x), int(y))
#         await asyncio.sleep(0.05)

#     except PWError as e:
#         msg = str(e).lower()
#         if "execution context was destroyed" in msg or "navigat" in msg:
#             # 导航竞态：等新文档 ready 再判断一次
#             try:
#                 await page.wait_for_load_state("domcontentloaded", timeout=5000)
#             except Exception:
#                 pass
#         else:
#             raise

#     # 点击后兜底判断：即使没有触发导航事件，但 URL/DOM 可能已经变了（SPA/同文档）
#     after = await _dom_signature(page)
#     if after != before:
#         return True  # 视为成功（同文档路由/动态更新等）
#     return True  # 或者根据你的需要返回 False；这里返回 True 表示点击已完成但未导航
    
@dataclass(frozen=True)
class BrowserGoalState(str,Enum):
    INITIAL = "initial"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass(frozen=True)
class Coordinate:
    x:int
    y:int

@dataclass(frozen=True)
class BrowserViewportDimensions():
    height:int
    width:int

@dataclass(frozen=True)
class ScrollBar():
    offset:float
    height:float

@dataclass(frozen=True)
class BrowserTab():
    handle: str
    url: str
    title: str
    active: bool
    new: bool
    id: int

@dataclass
class BrowserState():
    screenshot: str
    height: int   ##page.viewport_size, pixels
    width: int
    scrollbar: ScrollBar
    tabs: list[BrowserTab]
    active_tab: str
    mouse: Coordinate

@dataclass
class BrowserActionType(str,Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    KEY = "key"
    TYPE = "type"
    MOUSE_MOVE = "mouse_move"
    LEFT_CLICK = "left_click"
    LEFT_CLICK_DRAG = "left_click_drag"
    RIGHT_CLICK = "right_click"
    MIDDLE_CLICK = "middle_click"
    DOUBLE_CLICK = "double_click"
    SCREENSHOT = "screenshot"
    CURSOR_POSITION = "cursor_position"
    SWITCH_TAB = "switch_tab"
    SCROLL_DOWN = "scroll_down"
    SCROLL_UP = "scroll_up"

@dataclass(frozen=True)
class BrowserAction():
    action: BrowserActionType
    coordinate: Optional[Coordinate]
    text: Optional[str]
    reasoning: str
    id: str

@dataclass(frozen=True)
class BrowserStep():
    state: BrowserState
    action: BrowserAction

@dataclass(frozen=True)
class BrowserAgentOptions():
    additional_context:Optional[Union[str,dict[str,Any]]] = None
    additional_instructions:Optional[list[str]] = None
    wait_after_step_ms:Optional[int] = None
    pause_after_each_action:Optional[bool] = None
    max_steps:Optional[int] = None


class ActionPlanner(ABC):
    
    @abstractmethod
    def plan_action(
        self,
        goal: str,
        additional_context: str,
        additional_instructions: list[str],
        current_state: BrowserState,
        session_history: list[BrowserStep]
    ):
        pass


class BrowserAgent:
    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        action_planner: ActionPlanner,
        goal: str,
        options: Optional[BrowserAgentOptions] = None,
        wait_for_human: Optional[Callable[[str], None]] = None,
        on_step: Optional[Callable[[BrowserStep], None]] = None
    ) -> None:
        self.page = page
        self.context = context
        self.planner = action_planner
        self.goal = goal
        self.additional_context = "None"
        self.additional_instructions = []
        self.wait_after_step_ms = 500
        self.pause_after_each_action = False
        self.max_steps = 50
        self._status = BrowserGoalState.INITIAL
        self.history: list[BrowserStep] = []
        self.tabs: Dict[str, BrowserTab] = {}
        self._mouse_pos = Coordinate(1, 1)
        self.pause_on_challenge = getattr(self, "pause_on_challenge", PAUSE_ON_CHALLENGE)
        self.wait_for_human = wait_for_human or _default_cli_waiter_async
        self.on_step = on_step
        self._cap_flag = False
        self._last_side_effect = ""
        self._page_changing_actions = {"left_click", "right_click", "double_click", "type", "key"}
        # self._wire_challenge_network_hooks()

        if options:
            if options.additional_context:
                self.additional_context = (
                    json.dumps(options.additional_context)
                    if isinstance(options.additional_context, dict)
                    else options.additional_context
                )
            if options.additional_instructions:
                self.additional_instructions = options.additional_instructions
            if options.wait_after_step_ms:
                self.wait_after_step_ms = options.wait_after_step_ms
            if options.pause_after_each_action:
                self.pause_after_each_action = options.pause_after_each_action
            if options.max_steps:
                self.max_steps = options.max_steps
                
    @property
    def status(self) -> "BrowserGoalState":
        """只读状态（RUNNING / SUCCESS / FAILED）"""
        return _kind(self._status)
    
    async def get_state(self) -> BrowserState:
        viewport = self.page.viewport_size
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(100)
        # screenshot_bytes = await self.page.screenshot(full_page=False)
        screenshot_bytes = await screenshot_with_retry(self.page,full_page=False)
        mouse = await self.get_mouse_position()
        scrollbar = await self.get_scroll_position()

        browser_tabs = []
        pages = self.context.pages
        for idx, pg in enumerate(pages):
            url = pg.url
            
            # title = await pg.title()
            title = await read_with_retry(pg, pg.title)
            active = pg == self.page
            is_new = False
            handle = f"tab-{idx}"
            if handle not in self.tabs:
                is_new = True
            tab = BrowserTab(
                handle=handle,
                url=url,
                title=title,
                active=active,
                new=is_new,
                id=idx,
            )
            self.tabs[handle] = tab
            browser_tabs.append(tab)

        return BrowserState(
            screenshot=screenshot_bytes,
            height=viewport["height"],
            width=viewport["width"],
            scrollbar=scrollbar,
            tabs=browser_tabs,
            active_tab=f"tab-{pages.index(self.page)}",
            mouse=mouse,
        )

    async def get_scroll_position(self) -> ScrollBar:
        # offset, height = await self.page.evaluate(
        #     "() => [window.pageYOffset / document.documentElement.scrollHeight, window.innerHeight / document.documentElement.scrollHeight]"
        # )
        offset, height = await _safe_eval(self.page,
            "() => [window.pageYOffset / document.documentElement.scrollHeight, window.innerHeight / document.documentElement.scrollHeight]"
        )
        return ScrollBar(offset=offset, height=height)

    async def get_mouse_position(self) -> Coordinate:
        return self._mouse_pos

    def get_action(self, state: BrowserState) -> BrowserAction:
        return self.planner.plan_action(
            goal=self.goal,
            current_state=state,
            session_history=self.history,
            additional_context=self.additional_context,
            additional_instructions=self.additional_instructions,
        )
    async def take_action(self, action: BrowserAction, last_state: BrowserState) -> None:
        kb: Keyboard = self.page.keyboard
        m: Mouse = self.page.mouse
        action_kind = _kind(action.action)

        if action_kind == _kind(BrowserActionType.KEY):
            if not action.text:
                raise ValueError("Text required for key action")
            strokes = keys_mapping(action.text)
            for mod in strokes.modifiers:
                await kb.down(mod)
            for k in strokes.keys:
                # await kb.press(k)
                await safe_key(self.page, k)
            for mod in reversed(strokes.modifiers):
                await kb.up(mod)

        elif action_kind == _kind(BrowserActionType.TYPE):
            if not action.text:
                raise ValueError("Text required for type action")
            await kb.type(action.text)

        elif action_kind == _kind(BrowserActionType.MOUSE_MOVE):
            if not action.coordinate:
                raise ValueError("Coordinate required")
            await m.move(action.coordinate.x, action.coordinate.y)
            print("mouse moved to..", action.coordinate)
            self._mouse_pos = Coordinate(action.coordinate.x, action.coordinate.y)

        elif action_kind == _kind(BrowserActionType.LEFT_CLICK):
            print("last step mouse position:",self._mouse_pos)
            print("to left_click at", last_state.mouse)
            # await m.click(last_state.mouse.x, last_state.mouse.y)
            await safe_click_at(self.page, last_state.mouse.x, last_state.mouse.y)

        elif action_kind == _kind(BrowserActionType.SCROLL_DOWN):
            # await self.page.mouse.wheel(0, int(3 * last_state.height / 4))
            dy = int(0.75 * last_state.height)            # 和你之前等量
            await safe_scroll(self.page, dy)

        elif action_kind == _kind(BrowserActionType.SCROLL_UP):
            # await self.page.mouse.wheel(0, int(-3 * last_state.height / 4))
            dy = -int(0.75 * last_state.height)
            await safe_scroll(self.page, dy)

        elif action_kind == _kind(BrowserActionType.SWITCH_TAB):
            if not action.text:
                raise ValueError("Tab id required")
            idx = int(action.text)
            # self.page = self.context.pages[idx]
            newp = await switch_to_page(self.context, target_index=idx)
            if newp:
                self.page = newp

    async def step(self) -> None:
        state = await self.get_state()
        action = self.get_action(state)
        print("in step,Next action:", action)
        action_kind = _kind(action.action)
        print("in step:action_kind:", action_kind)

        if action_kind == "success":
            self._status = BrowserGoalState.SUCCESS
            return
        if action_kind == "failure":
            if self.pause_on_challenge and (_looks_like_captcha(action.reasoning)  or await detect_captcha_quick(self.page) ):
                try:
                    self.history.append(BrowserStep(state=state, action=action))
                except Exception:
                    pass
                await self.wait_for_human("CAPTCHA reported by model or detected on page")
                return
            self._status = BrowserGoalState.FAILED
            return

        self._status = BrowserGoalState.RUNNING
        await self.take_action(action, state)
        # await pause_if_captcha_then_screenshot(self.page, self.wait_for_human)
        # pause_if_captcha_then_screenshot(self.page, self.wait_for_human)
        step_obj = BrowserStep(state=state, action=action)
        self.history.append(step_obj)

        if self.on_step:
            try:
                await self.on_step(step_obj)
            except Exception:
                pass
    

    async def start(self) -> None:
        """Begin the automation loop."""
        # prime mouse listener
        await self.page.mouse.move(1, 1)

        while _kind(self._status) in ('initial', 'running') and len(self.history) <= self.max_steps:
            await self.step()
            print("in start, after step(),self._status:",self._status)
            print("in start,self._mouse_pos:",self._mouse_pos)
            

            await asyncio.sleep(self.wait_after_step_ms / 1000)

            # Optional pause after each step
            # if self.pause_after_each_action:
            #     await self.pause_for_input()  # Make sure pause_for_input is also async

        



    @property
    def status(self) -> BrowserGoalState:
        return self._status
