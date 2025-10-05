# human_pause.py
import os, sys, time, platform
from typing import List, Optional
from playwright.sync_api import TimeoutError as PWTimeoutError, Error as PWError,Page
import asyncio
_CAP_PATTERNS = ("captcha", "hcaptcha", "recaptcha", "challenge", "verify", "/sorry", "cloudflare", "cf-chl")

# 开关 & 超时，支持环境变量
PAUSE_ON_CHALLENGE = os.getenv("PAUSE_ON_CHALLENGE", "1") == "1"
HUMAN_PAUSE_TIMEOUT = int(os.getenv("HUMAN_PAUSE_TIMEOUT", "0"))  # 0=无限等

# 常见挑战控件（可按需要增删）
CHALLENGE_SELECTORS: List[str] = [
    'iframe[title*="captcha"]',
    'iframe[src*="captcha"]',
    '#captcha', '[name="captcha"]',
    '[aria-label*="challenge"]',
    '[class*="captcha"]', '[id*="challenge"]',
]

_NEEDLES = ("captcha", "hcaptcha", "recaptcha", "challenge", "verify")

def is_challenge_present0(page: Page, timeout_ms: int = 1000) -> bool:
    """
    返回 True 表示检测到验证码/挑战；False 表示未检测到。
    不向外抛 TimeoutError。
    """
    for sel in CHALLENGE_SELECTORS:
        try:
            # 先做一次“无等待”的快速检查，不会抛异常
            if page.locator(sel).first.is_visible():
                return True
            # 再做一次短等待（可能刚好晚一点出现）
            page.locator(sel).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PWTimeoutError:
            # 本选择器在指定时间内没出现，继续下一个
            continue
        except Exception:
            # 其它异常一律忽略（可按需 print 调试）
            continue

    # 再在 frame 里粗查一遍（URL/名称里带 captcha/challenge/verify）
    try:
        for f in page.frames:
            u = (f.url or "").lower()
            n = (f.name or "").lower()
            if any(k in u for k in ("captcha", "challenge", "verify", "hcaptcha", "recaptcha")) \
               or any(k in n for k in ("captcha", "challenge", "verify")):
                return True
            for sel in CHALLENGE_SELECTORS:
                try:
                    if f.locator(sel).first.is_visible():
                        return True
                except Exception:
                    pass
    except Exception:
        pass

    return False

def _frame_has_challenge(frame) -> bool:
    """
    Instant (no-wait) scan inside a frame using evaluate.
    Returns False if the frame is navigating or just got destroyed.
    """
    try:
        return frame.evaluate(
            """(needles) => {
              const lower = s => (s ?? '').toString().toLowerCase();
              const has = s => {
                const t = lower(s);
                return needles.some(n => t.includes(n));
              };

              // 1) iframe title/src hints
              for (const f of document.querySelectorAll('iframe')) {
                if (has(f.getAttribute('title')) || has(f.getAttribute('src'))) return true;
              }

              // 2) common attributes on any element
              const attrs = ['id','class','name','aria-label'];
              for (const el of document.querySelectorAll('*')) {
                for (const a of attrs) {
                  if (has(el.getAttribute(a))) return true;
                }
              }
              return false;
            }""",
            list(_NEEDLES),
        )
    except PWError:
        # frame is navigating / context destroyed right now — ignore this tick
        return False
    except Exception:
        return False

def is_challenge_present(page: Page, timeout_ms: int = 1500, poll_ms: int = 150) -> bool:
    """
    Poll up to timeout_ms to detect captcha/challenge.
    Only uses page.url + main-frame evaluate (no frame enumerate / no locators / no waits).
    Never raises; returns True (found) or False (not found).
    """
    deadline = time.time() + timeout_ms / 1000.0

    while time.time() < deadline:
        if page.is_closed():
            return False

        # 0) URL hints (doesn't depend on JS context)
        try:
            u = (page.url or "").lower()
            if any(n in u for n in _NEEDLES) or "/sorry" in u:
                return True
        except Exception:
            # page may be mid-navigation; ignore this tick
            pass

        # 1) Main-frame, instant JS checks (no waits)
        # try:
        #     # any iframe on the page that "looks like" a challenge?
        #     iframe_hit = page.evaluate(
        #         """(needles) => {
        #             const has = s => (s ?? '').toString().toLowerCase();
        #             for (const f of document.querySelectorAll('iframe')) {
        #               const t = has(f.getAttribute('title'));
        #               const s = has(f.getAttribute('src'));
        #               if (needles.some(n => t.includes(n) || s.includes(n))) return true;
        #             }
        #             return false;
        #         }""",
        #         list(_NEEDLES),
        #     )
        #     if iframe_hit:
        #         return True

        #     # obvious attributes on main-frame elements
        #     main_hit = page.evaluate(
        #         """(needles) => {
        #             const qs = '[id*="captcha" i],[class*="captcha" i],[name*="captcha" i],[aria-label*="captcha" i],'
        #                       + '[id*="challenge" i],[class*="challenge" i],[aria-label*="challenge" i]';
        #             const el = document.querySelector(qs);
        #             if (!el) return false;
        #             // quick sanity on visible-ish
        #             const r = el.getBoundingClientRect();
        #             return r && r.width >= 1 && r.height >= 1;
        #         }""",
        #         list(_NEEDLES),
        #     )
        #     if main_hit:
        #         return True

        # except Exception:
        #     # if the JS context was destroyed (navigation), just retry next tick
        #     pass

        time.sleep(poll_ms / 1000.0)

    return False

def _read_key_nonblock(timeout_s: int) -> Optional[str]:
    """跨平台非阻塞等待输入：返回按键（Enter 返回空字符串），或 None 表示超时。"""
    end = time.time() + timeout_s
    if platform.system() == "Windows":
        import msvcrt
        buf = ""
        while time.time() < end:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch == "\r":  # Enter
                    return buf
                elif ch in ("\n",):
                    return buf
                else:
                    buf += ch
            time.sleep(0.1)
        return None
    else:
        import select
        r, _, _ = select.select([sys.stdin], [], [], timeout_s)
        if r:
            return sys.stdin.readline().rstrip("\n")
        return None

def wait_for_human0(reason: str, timeout_s: int = HUMAN_PAUSE_TIMEOUT) -> str:
    """
    停下等待人工处理。
    - 回车/空输入：继续
    - 输入 s：跳过本步
    - 输入 q：退出/抛异常
    - 超时（如果设置了 timeout_s>0）：自动继续
    """
    msg = f"⚠️ Detected capcha：{reason}\n" \
          f"→ please complete in browser manually then press Enter to continue, press s to skip,press q to quit\n"
    if timeout_s > 0:
        msg += f"(will wait for {timeout_s}s, timeout will continue automatically)\n"
    print(msg, flush=True)

    if timeout_s <= 0:
        # 阻塞等待
        ans = input().strip().lower()
    else:
        ans = _read_key_nonblock(timeout_s)
        if ans is None:
            print("[human_pause] timeout，continue automatically", flush=True)

            return ""
        ans = ans.strip().lower()

    if ans == "q":
        raise KeyboardInterrupt("user choose to quit（q）")
    elif ans == "s":
        return "skip"
    else:
        return ""


async def detect_captcha_quick(page) -> bool:
    """Fast detect captcha by URL patterns."""
    try:
        await asyncio.sleep(1)
        u = (page.url or "").lower()
        print("page url:")
        print(u)
        if any(p in u for p in _CAP_PATTERNS):
            return True
    except Exception:
        pass
    try:
        for fr in page.frames:
            fu = (fr.url or "").lower()
            if any(p in fu for p in _CAP_PATTERNS):
                return True
    except Exception:
        pass
    return False

async def pause_if_captcha_then_screenshot(page,wait_for_human):
    """
    found captcha -> wait for user handling -> return screenshot bits after resolved
    No captcha -> return None
    
    """
    if not await detect_captcha_quick(page):
        return None
    print("[captcha] detected. Please complete the captcha in the browser, then press Enter to continue...")
    # input("After completing the captcha, press Enter to continue...")
    await wait_for_human(reason="captcha")
    try:
        return await page.screenshot(full_page=False)
    except Exception:
        return None