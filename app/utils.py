from typing import NamedTuple, Optional
import asyncio
from playwright.async_api import Error as PwError, TimeoutError as PwTimeout
from playwright._impl._errors import Error as PWError


class KeyMapping(NamedTuple):
    """Class for keys and modifiers return."""

    modifiers: list[str]
    keys: list[str]

def keys_mapping(xdotool_command: str):
    # Handle splitting and stripping leading/trailing whitespace
    key_parts = [part.strip().lower() for part in xdotool_command.split("+")]

    # Dictionary mapping xdotool keys to Selenium Keys constants
    key_mapping = {
        "ctrl": "Control",
        "control": "Control",
        "alt": "Alt",
        "shift": "Shift",
        "super": "Meta",
        "command": "Meta",
        "meta": "Meta",
        "win": "Meta",
        "cmd":"Meta",
        "cancel": "Cancel",
        "help": "Help",
        "backspace": "Backspace",
        "back_space": "Backspace",
        "tab": "Tab",
        "clear": "Clear",
        "return": "Enter",
        "enter": "Enter",
        "pause": "Pause",
        "escape": "Escape",
        "esc":"Escape",
        "space": "Space",
        "pageup": "PageUp",
        "page_up": "PageUp",
        "pgup":"PageUp",
        "pagedown": "PageDown",
        "page_down": "PageDown",
        "pgdn":"PageDown",
        "end": "End",
        "home": "Home",
        "left": "ArrowLeft",
        "arrowleft": "ArrowLeft",
        "arrow_left": "ArrowLeft",
        "up": "ArrowUp",
        "arrowup": "ArrowUp",
        "arrow_up": "ArrowUp",
        "right": "ArrowRight",
        "arrowright": "ArrowRight",
        "arrow_right": "ArrowRight",
        "down": "ArrowDown",
        "arrowdown": "ArrowDown",
        "arrow_down": "ArrowDown",
        "insert": "Insert",
        "delete": "Delete",
        "semicolon": ";",
        "equals": "=",
        "kp_0": "Numpad0",
        "kp_1": "Numpad1",
        "kp_2": "Numpad2",
        "kp_3": "Numpad3",
        "kp_4": "Numpad4",
        "kp_5": "Numpad5",
        "kp_6": "Numpad6",
        "kp_7": "Numpad7",
        "kp_8": "Numpad8",
        "kp_9": "Numpad9",
        "multiply": "NumpadMultiply",
        "add": "NumpadAdd",
        "separator": "NumpadComma",
        "subtract": "NumpadSubtract",
        "decimal": "NumpadDecimal",
        "divide": "NumpadDivide",
        "f1": "F1",
        "f2": "F2",
        "f3": "F3",
        "f4": "F4",
        "f5": "F5",
        "f6": "F6",
        "f7": "F7",
        "f8": "F8",
        "f9": "F9",
        "f10": "F10",
        "f11": "F11",
        "f12": "F12",
    }

    modifiers = [
        key_mapping.get(part.lower(), part)
        for part in key_parts
        if part.lower() in ["ctrl", "alt", "shift", "super", "command", "meta"]
    ]

    keys = [
        key_mapping.get(part.lower(), part)
        for part in key_parts
        if part.lower() not in ["ctrl", "alt", "shift", "super", "command", "meta"]
    ]

    return KeyMapping(modifiers=modifiers, keys=keys)

async def read_with_retry(page, op, *args, retries=3, backoff=0.12):
    for i in range(retries):
        try:
            await page.wait_for_load_state("domcontentloaded")
            return await op(*args)         # 例如 op=page.title
        except PwError as e:
            if "Execution context was destroyed" in str(e) and i < retries-1:
                await asyncio.sleep(backoff * (i + 1))  # 小退避后重试
                continue
            raise
        
async def screenshot_with_retry(page, *, retries=3, backoff=0.15, **kwargs):
    """
    统一在 DOM 就绪后截图；遇到导航/上下文销毁/慢渲染时短退避重试。
    kwargs 直接透传给 page.screenshot()（如 path=、full_page= 等）
    """
    for i in range(retries + 1):
        try:
            await page.wait_for_load_state("domcontentloaded")
            # 关动画，减少“拍不到稳定帧”导致的超时
            return await page.screenshot(animations="disabled", timeout=45000, **kwargs)
        except (PwTimeout, PwError) as e:
            s = str(e)
            transient = (
                "Execution context was destroyed" in s
                or "Target closed" in s
                or "waiting for fonts" in s
                or "taking page screenshot" in s
            )
            if transient and i < retries:
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(backoff * (i + 1))  # 0.15s, 0.30s …
                # 第一次重试尽量不用 full_page（更快更稳）
                if i == 0 and kwargs.get("full_page", False):
                    kwargs = {**kwargs, "full_page": False}
                continue
            raise
        
async def _safe_eval(page, script: str):
    try:
        return await page.evaluate(script)
    except PwError as e:
        m = str(e).lower()
        if "execution context was destroyed" in m or "because of a navigation" in m:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            return await page.evaluate(script)
        raise
    


# async def dom_sig(page):
#     try:
#         return await page.evaluate("() => location.href + '|' + (document.body?.innerText?.length||0)")
#     except Exception:
#         return page.url + "|?"

# async def wait_document_ready(page, timeout=8000):
#     await page.wait_for_function(
#         "() => ['interactive','complete'].includes(document.readyState)", timeout=timeout
#     )

# async def wait_layout_stable(page, timeout=8000, frames_ok=4, interval_ms=120):
#     js = f"""
#     (n, dt) => new Promise(res => {{
#       let ok=0, last=document.body?.getBoundingClientRect().height||0;
#       const id=setInterval(()=>{{
#         const h=document.body?.getBoundingClientRect().height||0;
#         ok = Math.abs(h-last) < 1 ? ok+1 : 0;
#         last=h;
#         if(ok>=n){{clearInterval(id);res(true);}}
#       }}, dt);
#       setTimeout(()=>{{clearInterval(id);res(false);}}, {timeout});
#     }})
#     """
#     try:
#         await page.evaluate(js, frames_ok, interval_ms)
#     except Exception:
#         pass

# async def safe_eval(page, code):
#     try:
#         return await page.evaluate(code)
#     except PwError as e:
#         m = str(e).lower()
#         if "execution context was destroyed" in m or "navigat" in m:
#             try: await page.wait_for_load_state("domcontentloaded", timeout=5000)
#             except Exception: pass
#             return await page.evaluate(code)
#         raise

# async def safe_key(page, key: str, timeout_nav=10000):
#     k = (key or "").strip()
#     if k.lower() == "return":
#         k = "Enter"

#     # 是否可能引发导航（可按需扩展）
#     nav_keys = {"Enter", "Alt+Left", "Alt+Right"}
#     # 也可结合当前 activeElement 判断：输入框里的 Enter 才视为 nav likely

#     if k in nav_keys:
#         async with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout_nav):
#             await page.keyboard.press(k)
#         return True

#     # 非导航：确保焦点存在，避免打到空处
#     try:
#         focused = await safe_eval(page, "()=>document.activeElement && document.activeElement !== document.body")
#         if not focused:
#             await page.focus("body")
#     except Exception:
#         pass

#     await page.keyboard.press(k)
#     await asyncio.sleep(0.05)  # 微沉淀
#     return True

# async def safe_scroll(page, dy: int, dx: int = 0):
#     # 使用鼠标滚轮比直接 evaluate scroll 更接近真实用户
#     await page.mouse.wheel(dx=dx, dy=dy)
#     # 等 1~2 帧布局稳定
#     await wait_layout_stable(page, timeout=2000, frames_ok=2, interval_ms=80)
#     return True

# # 你的接口可以包装成：
# async def scroll_down(page, amount=800):
#     return await safe_scroll(page, amount)

# async def scroll_up(page, amount=800):
#     return await safe_scroll(page, -amount)



# ========== 共同的小工具 ==========
async def dom_sig(page):
    """轻量判断页面是否变化（支持 SPA / 局部更新）"""
    try:
        return await page.evaluate(
            "() => location.href + '|' + (document.title||'') + '|' + (document.body?.innerText?.length||0)"
        )
    except Exception:
        return page.url + "|?"

async def wait_document_ready(page, timeout=8000):
    await page.wait_for_function(
        "() => ['interactive','complete'].includes(document.readyState)", timeout=timeout
    )

async def wait_layout_stable(page, timeout=2000, frames_ok=2, interval_ms=80):
    """连续 N 帧 body 高度几乎不变，视为布局稳定；比 networkidle 更鲁棒"""
    js = f"""
    (n, dt) => new Promise(res => {{
      let ok=0, last=document.body?.getBoundingClientRect().height||0;
      const id=setInterval(()=>{{
        const h=document.body?.getBoundingClientRect().height||0;
        ok = Math.abs(h-last) < 1 ? ok+1 : 0;
        last=h;
        if(ok>=n){{clearInterval(id);res(true);}}
      }}, dt);
      setTimeout(()=>{{clearInterval(id);res(false);}}, {timeout});
    }})
    """
    try:
        await page.evaluate(js, [int(frames_ok), int(interval_ms), int(timeout)])
    except Exception:
        pass

async def safe_eval(page, code):
    """在导航竞态下自动重试一次的 evaluate 包装"""
    try:
        return await page.evaluate(code)
    except PWError as e:
        m = str(e).lower()
        if "execution context was destroyed" in m or "navigat" in m:
            try: await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception: pass
            return await page.evaluate(code)
        raise
    
async def scroll_metrics(page):
    # 返回滚动位置/总高/视口高，避免 0 除
    return await _safe_eval(page, """
      () => {
        const de = document.documentElement;
        const root = document.scrollingElement || de;
        const top = root.scrollTop || window.pageYOffset || 0;
        const total = Math.max(1, root.scrollHeight || de.scrollHeight || 1);
        const vh = Math.max(1, de.clientHeight || window.innerHeight || 1);
        return {top, total, vh};
      }
    """)

# ========== 坐标点击专用的前置探测 ==========
async def maybe_scroll_into_view(page, x, y):
    """仅当坐标不在视口时，滚动到视口中部"""
    vp = await page.evaluate("() => ({w: innerWidth, h: innerHeight, sx: scrollX, sy: scrollY})")
    if 0 <= x < vp["w"] and 0 <= y < vp["h"]:
        return False
    await page.evaluate(
        "([x,y,sy]) => window.scrollTo({top: Math.max(0, y + sy - innerHeight/2), behavior:'instant'})",
        [x, y, vp["sy"]],
    )
    return True

async def probe_point(page, x, y):
    """
    —— 你问的 _probe_point()（通用版）——
    用 elementFromPoint 判断当前命中的元素是否可见/可点，
    以及是否“可能导航”或“可能新开页”。
    """
    js = """
    ([x,y]) => {
      const el = document.elementFromPoint(x,y);
      if (!el) return null;
      const cs = getComputedStyle(el);
      const visible = cs && cs.visibility!=='hidden' && cs.display!=='none' && parseFloat(cs.opacity||'1')>0.01;
      const pe = cs && cs.pointerEvents!=='none';
      const link = el.closest('a[href], [role="link"][href]');
      const submit = el.closest('button[type="submit"], input[type="submit"]');
      const newTab = link && (link.target==='_blank' || (link.rel||'').includes('noopener'));
      return { visible, pe, navLikely: !!(link||submit), popupLikely: !!newTab };
    }
    """
    return await page.evaluate(js, [x, y])

# ========== 统一的安全 Click / Key / Scroll / Tabs / History ==========
async def safe_click_at(page, x: int, y: int, nav_timeout=10000) -> bool:
    """站点无关、坐标优先的安全点击：就绪→探测→选择合适等待→一次竞态重试"""
    before = await dom_sig(page)
    await wait_document_ready(page)
    await maybe_scroll_into_view(page, x, y)
    await wait_layout_stable(page)

    info = await probe_point(page, x, y)
    if not info or not (info["visible"] and info["pe"]):
        # 布局还在动/懒加载，再等 120ms 再看一次
        await asyncio.sleep(0.12)
        info = await probe_point(page, x, y)
        if not info or not (info["visible"] and info["pe"]):
            return False  # 不盲点，交由上层看门狗/重试策略

    try:
        if info.get("popupLikely"):  # 可能 target=_blank
            async with page.expect_popup() as pctx:
                await page.mouse.click(int(x), int(y))
            newp = await pctx.value    # ← 注意 await
            await newp.wait_for_load_state("domcontentloaded")
            # 调用方（BrowserAgent）如果有 self.page，记得切到 newp
            return True

        if info.get("navLikely"):
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=nav_timeout):
                await page.mouse.click(int(x), int(y))
            return True

        await page.mouse.click(int(x), int(y))     # 非导航点击
        await asyncio.sleep(0.05)                  # 微沉淀
    except PWError as e:
        msg = str(e).lower()
        if "execution context was destroyed" in msg or "navigat" in msg:
            try: await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception: pass
        else:
            raise

    # SPA / 同文档变化兜底
    after = await dom_sig(page)
    return after != before or True

async def safe_key(page, key: str, timeout_nav=10000) -> bool:
    k = (key or "").strip()
    if k.lower() == "return":
        k = "Enter"

    # 可能导航的键（可按需扩展/判断 activeElement）
    nav_keys = {"Enter", "Alt+Left", "Alt+Right"}
    if k in nav_keys:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout_nav):
            await page.keyboard.press(k)
        return True

    # 非导航键：确保有焦点，避免打到空处
    try:
        focused = await safe_eval(page, "() => document.activeElement && document.activeElement !== document.body")
        if not focused:
            await page.focus("body")
    except Exception:
        pass
    await page.keyboard.press(k)
    await asyncio.sleep(0.05)
    return True

async def safe_scroll(page, dy: int, dx: int = 0) -> bool:
    before = await scroll_metrics(page)

    # 执行滚轮滚动
    await page.mouse.wheel(dx=dx, dy=int(dy))

    # 等待两帧布局稳定（懒加载/重排落地）
    await wait_layout_stable(page, timeout=1200, frames_ok=2, interval_ms=60)

    # 校验是否真的滚动了
    after = await scroll_metrics(page)
    if after["top"] != before["top"]:
        return True

    # 一次性轻重试：有些页面阻止了滚轮，尝试 scrollBy
    await _safe_eval(page, f"() => window.scrollBy({{top:{int(dy)}, left:{int(dx)}, behavior:'instant'}})")
    await wait_layout_stable(page, timeout=800, frames_ok=2, interval_ms=60)
    after2 = await scroll_metrics(page)
    return after2["top"] != before["top"]

async def switch_to_page(context, target_index: int = -1):
    pages = context.pages
    if not pages:
        return None
    target = pages[-1] if target_index < 0 else pages[min(target_index, len(pages)-1)]
    await target.bring_to_front()
    await target.wait_for_load_state("domcontentloaded")
    return target

async def safe_go_back(page, timeout_nav=10000):
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout_nav):
        await page.go_back()
    return True

async def safe_go_forward(page, timeout_nav=10000):
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout_nav):
        await page.go_forward()
    return True



