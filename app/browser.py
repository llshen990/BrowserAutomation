# browser_playwright.py

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union, Dict

from utils import keys_mapping
from playwright.sync_api import Page, BrowserContext, Keyboard, Mouse
from human_pause import is_challenge_present, wait_for_human, PAUSE_ON_CHALLENGE


def _kind(v):
    # Prefer Enum.value when available, else use v
    val = getattr(v, "value", v)
    if isinstance(val, str):
        return val.strip().lower()
    return str(val).strip().lower()
    
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
    """Playwright-based agent class for browser automation."""

    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        action_planner: ActionPlanner,
        goal: str,
        options: Optional[BrowserAgentOptions] = None,
    ) -> None:
        self.page: Page = page
        self.context: BrowserContext = context
        self.planner = action_planner
        self.goal = goal
        self.additional_context = "None"
        self.additional_instructions: list[str] = []
        self.wait_after_step_ms = 500
        self.pause_after_each_action = False
        self.max_steps = 50
        self._status = BrowserGoalState.INITIAL
        self.history: list[BrowserStep] = []
        # map handle (page.context.pages index or popup) to BrowserTab
        self.tabs: Dict[str, BrowserTab] = {}
        self._mouse_pos = Coordinate(1, 1)
        self.pause_on_challenge = getattr(self, "pause_on_challenge", PAUSE_ON_CHALLENGE)

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

    def get_state(self) -> BrowserState:
        """Get current browser state via Playwright."""
        viewport = self.page.viewport_size
        # Playwright returns bytes; encode to base64 for consistency
        screenshot_bytes = self.page.screenshot(full_page=False)
        screenshot_b64 = screenshot_bytes.encode("base64") if isinstance(screenshot_bytes, str) else screenshot_bytes
        
        mouse = self.get_mouse_position()
        
        scrollbar = self.get_scroll_position()

        # collect tabs from context
        browser_tabs = []
        pages = self.context.pages
        for idx, pg in enumerate(pages):
            url = pg.url
            title = pg.title()
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
            screenshot=screenshot_b64,
            height=viewport["height"],
            width=viewport["width"],
            scrollbar=scrollbar,
            tabs=browser_tabs,
            active_tab=f"tab-{pages.index(self.page)}",
            mouse=mouse,
        )

    def get_scroll_position(self) -> ScrollBar:
        """Get current scroll position as fraction."""
        offset, height = self.page.evaluate(
        "() => [                       \
            window.pageYOffset / document.documentElement.scrollHeight, \
            window.innerHeight  / document.documentElement.scrollHeight \
        ]"
        )
        # offset, height = self.page.evaluate(
        #     "(window.pageYOffset/document.documentElement.scrollHeight, "
        #     "window.innerHeight/document.documentElement.scrollHeight)"
        # )
        return ScrollBar(offset=offset, height=height)

    def _set_mouse(self, x: int, y: int, clamp_to_viewport: bool = True):
        if clamp_to_viewport:
            vw, vh = self.page.evaluate("([window.innerWidth, window.innerHeight])")
            x = max(0, min(int(x), int(vw) - 1))
            y = max(0, min(int(y), int(vh) - 1))
        self._mouse_pos = Coordinate(x, y)

    def get_mouse_position(self) -> Coordinate:
        print("get_mouse_position:")
        print(self._mouse_pos)
        return self._mouse_pos

    def get_mouse_position1(self) -> Coordinate:
        """Approximate mouse position via injected listener."""
        # Inject listener
        self.page.evaluate(
            """
            window._last_mouse = {x:0,y:0};
            document.addEventListener('mousemove', e => {
                window._last_mouse.x = e.clientX;
                window._last_mouse.y = e.clientY;
            });
            """
        )
        # Jiggle the mouse so that listener fires
        self.page.mouse.move(1, 1)
        # self.page.mouse.move(0, 0)
        time.sleep(0.1)
        last = self.page.evaluate("window._last_mouse")
        print(last)
        return Coordinate(x=int(last["x"]), y=int(last["y"]))

    def get_action(self, current_state: BrowserState) -> BrowserAction:
        return self.planner.plan_action(
            self.goal,
            self.additional_context,
            self.additional_instructions,
            current_state,
            self.history,
        )

    def take_action(self, action: BrowserAction, last_state: BrowserState) -> None:
        """Execute an action via Playwright's page, keyboard, and mouse APIs."""
        kb: Keyboard = self.page.keyboard
        m: Mouse = self.page.mouse
        
        if self.pause_on_challenge and is_challenge_present(self.page, timeout_ms=300):
            res = wait_for_human("执行动作前检测到挑战")
            if res == "skip":
                print("[challenge] 用户选择跳过本动作")
                return
        
        if _kind(action.action) == _kind(BrowserActionType.KEY):
            if not action.text:
                raise ValueError("Text required for key action")
            strokes = keys_mapping(action.text)
            for mod in strokes.modifiers:
                kb.down(mod)
            for k in strokes.keys:
                kb.press(k)
            for mod in reversed(strokes.modifiers):
                kb.up(mod)

        elif _kind(action.action) == _kind(BrowserActionType.TYPE):
            if not action.text:
                raise ValueError("Text required for type action")
            kb.type(action.text)

        elif _kind(action.action) == _kind(BrowserActionType.MOUSE_MOVE):
            if not action.coordinate:
                raise ValueError("Coordinate required")
            print("BrowserActionType.MOUSE_MOVE,action.coordinate:")
            print(action.coordinate)
            m.move(action.coordinate.x, action.coordinate.y)
            self._set_mouse(action.coordinate.x, action.coordinate.y)

        elif _kind(action.action) == _kind(BrowserActionType.LEFT_CLICK):
            m.click(last_state.mouse.x, last_state.mouse.y)

        elif _kind(action.action) == _kind(BrowserActionType.LEFT_CLICK_DRAG):
            if not action.coordinate:
                raise ValueError("Coordinate required")
            m.down()
            m.move(action.coordinate.x, action.coordinate.y)
            m.up()

        elif _kind(action.action) == _kind(BrowserActionType.RIGHT_CLICK):
            m.click(last_state.mouse.x, last_state.mouse.y, button="right")

        elif _kind(action.action) == _kind(BrowserActionType.DOUBLE_CLICK):
            m.dblclick(last_state.mouse.x, last_state.mouse.y)

        elif _kind(action.action) == _kind(BrowserActionType.SCROLL_DOWN):
            self.page.mouse.wheel(0, int(3 * last_state.height / 4))

        elif _kind(action.action) == _kind(BrowserActionType.SCROLL_UP):
            self.page.mouse.wheel(0, int(-3 * last_state.height / 4))

        elif _kind(action.action) == _kind(BrowserActionType.SWITCH_TAB):
            if not action.text:
                raise ValueError("Tab id required")
            target = f"tab-{action.text}"
            pages = self.context.pages
            idx = int(action.text)
            self.page = pages[idx]

        else:
            # SCREENSHOT, CURSOR_POSITION, FAILURE/SUCCESS are no-ops
            pass
        
        if self.pause_on_challenge and is_challenge_present(self.page, timeout_ms=300):
            res = wait_for_human("执行动作后检测到挑战")
            if res == "skip":
                print("[challenge] 用户选择跳过后续（本步后）")

    def step(self) -> None:
        state = self.get_state()
        action = self.get_action(state)
        print("step,get_action result..")
        print(action)
        action_kind = _kind(action.action)
        print(action_kind)
        if action_kind == "success":            
            self._status = BrowserGoalState.SUCCESS
            return
        if action_kind == "failure":            
            self._status = BrowserGoalState.FAILED
            return
        
        self._status = BrowserGoalState.RUNNING        
        self.take_action(action, state)
        self.history.append(BrowserStep(state=state, action=action))

    def start(self) -> None:
        """Begin the automation loop."""
        # prime mouse listener
        self.page.mouse.move(1, 1)
        
               
        while _kind(self._status) in ('initial', 'running') and len(self.history) <= self.max_steps:

            self.step()
            print("browser.py line358")

            print(self._status)
            print(_kind(self._status) == "running")

            time.sleep(self.wait_after_step_ms / 1000)
            # if self.pause_after_each_action:
            #     pause_for_input()
        print("browser.py line366")
        print(self._status)
        print("Ended")

    @property
    def status(self) -> BrowserGoalState:
        return self._status


class SimplePlanner(ActionPlanner):
    def plan_action(self, observation, **kwargs):
        
        return {"type": "noop"}