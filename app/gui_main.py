# gui_main.py  — PyQt5 GUI with system keyring support + persistent asyncio loop
import os
import sys
import asyncio
import threading
import traceback
from pathlib import Path
from typing import Optional

from PyQt5 import QtCore, QtWidgets
from playwright.async_api import async_playwright

# === your existing imports ===
from browser import BrowserAgent, BrowserAgentOptions, HITLPause
from anthropicAgent import AnthropicPlanner


# === NEW: keyring for OS-level secret storage ===
try:
    import keyring
    KEYRING_AVAILABLE = True
except Exception:
    KEYRING_AVAILABLE = False

SERVICE = "MyAgentApp"   # 可改成你的应用名
ACCOUNT = "anthropic"    # 可按需区分用户/环境

def _user_ms_playwright_dir() -> str:
    # Cross-platform user cache location for ms-playwright
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return str(Path(base) / "ms-playwright")
    elif sys.platform == "darwin":
        return str(Path.home() / "Library" / "Caches" / "ms-playwright")
    else:
        return str(Path.home() / ".cache" / "ms-playwright")

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _user_ms_playwright_dir()
async def _try_launch_once():
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(headless=True)
        await browser.close()
    finally:
        await pw.stop()

def ensure_playwright_browsers_blocking():
    """若未安装浏览器，自动执行 playwright install chromium。"""
    try:
        asyncio.run(_try_launch_once())
        return
    except Exception:
        try:
            from playwright.__main__ import main as pw_cli_main
            sys.argv = ["playwright", "install", "chromium"]
            pw_cli_main()
        except SystemExit:
            pass
        asyncio.run(_try_launch_once())
        
def load_api_key_from_keyring() -> str:
    if not KEYRING_AVAILABLE:
        return ""
    try:
        v = keyring.get_password(SERVICE, ACCOUNT)
        return v or ""
    except Exception:
        return ""

def save_api_key_to_keyring(key: str) -> bool:
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.set_password(SERVICE, ACCOUNT, key)
        return True
    except Exception:
        return False

def delete_api_key_from_keyring() -> bool:
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.delete_password(SERVICE, ACCOUNT)
        return True
    except Exception:
        return False

def _is_hitl_pause(e: BaseException) -> bool:
    # 以名称判断，避免跨模块异常类不相等的问题（browser.HITLPause vs human_pause.HITLPause）
    return e.__class__.__name__ == "HITLPause"


class Worker(QtCore.QObject):
    """
    Runs Playwright + BrowserAgent on a single, persistent asyncio loop.
    """
    # Signals back to UI
    log = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    hitl = QtCore.pyqtSignal(str)
    ready = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key  # === NEW: keep key only in memory ===
        self._goal: Optional[str] = None

        # Async loop + runtime
        self._aloop: Optional[asyncio.AbstractEventLoop] = None
        self._aloop_thread: Optional[threading.Thread] = None
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._agent: Optional[BrowserAgent] = None
        self._initialized = False
        self._running = False

        self._ensure_async_loop()

    # ---------- Async loop lifecycle ----------
    def _ensure_async_loop(self):
        if self._aloop is not None:
            return
        self._aloop = asyncio.new_event_loop()

        def _run():
            try:
                asyncio.set_event_loop(self._aloop)
                self._aloop.run_forever()
            finally:
                try:
                    self._aloop.close()
                except Exception:
                    pass

        self._aloop_thread = threading.Thread(target=_run, name="WorkerAsyncLoop", daemon=True)
        self._aloop_thread.start()

    # ---------- Public slots from UI ----------
    @QtCore.pyqtSlot(str)
    def set_goal(self, goal: str):
        self._goal = goal

    @QtCore.pyqtSlot(str)
    def set_api_key(self, key: str):
        # 仅在内存持有，不打印、不落盘
        self.api_key = key or ""

    @QtCore.pyqtSlot()
    def run(self):
        if not self._aloop:
            self._ensure_async_loop()

        def _done(fut: asyncio.Future):
            exc = fut.exception()
            if exc:
                self.error.emit(f"Init/Run crashed: {exc!r}\n{traceback.format_exc()}")
                self.finished.emit()

        if not self._initialized:
            fut = asyncio.run_coroutine_threadsafe(self._init_async(self._goal or ""), self._aloop)
            fut.add_done_callback(_done)
        else:
            fut = asyncio.run_coroutine_threadsafe(self._step_loop_async(), self._aloop)
            fut.add_done_callback(lambda f: self.finished.emit())

    @QtCore.pyqtSlot()
    def shutdown(self):
        if not self._aloop:
            return

        async def _cleanup():
            try:
                if self._context: await self._context.close()
            except Exception: pass
            try:
                if self._browser: await self._browser.close()
            except Exception: pass
            try:
                if self._pw: await self._pw.stop()
            except Exception: pass

        try:
            fut = asyncio.run_coroutine_threadsafe(_cleanup(), self._aloop)
            fut.result(timeout=5)
        except Exception:
            pass

        self._agent = self._pw = self._browser = self._context = self._page = None
        self._initialized = False

    # ---------- Async coroutines (on persistent loop) ----------
    async def _init_async(self, goal: str):
        try:
            # 优先环境变量（不覆盖已手动设置的 self.api_key）
            env_key = os.environ.get("apikey", "")
            effective_key = self.api_key or env_key or load_api_key_from_keyring()
            # 放入进程环境供下游 SDK 使用（不打印）
            if effective_key:
                os.environ["apikey"] = effective_key

            if not self._pw:
                self._pw = await async_playwright().start()
            if not self._browser:
                self._browser = await self._pw.chromium.launch(headless=False)
            if not self._context:
                self._context = await self._browser.new_context()
            if not self._page:
                self._page = await self._context.new_page()
                await self._page.goto("https://www.google.com")

            planner = AnthropicPlanner()
            options = BrowserAgentOptions(max_steps=20)

            async def wait_for_human(reason: str = ""):
                msg = reason or "Please complete CAPTCHA / consent."
                self.hitl.emit(msg)
                # 统一抛出名字为 HITLPause 的异常，由上层按名称捕获
                class _TmpPause(Exception): pass
                try:
                    from human_pause import HITLPause as _HP  # 若可用，用同一个类
                    raise _HP(msg)
                except Exception:
                    # 兜底：抛出名字相同的异常类型（供 __name__ 匹配）
                    _TmpPause.__name__ = "HITLPause"
                    raise _TmpPause(msg)

            if not self._agent:
                self._agent = BrowserAgent(
                    page=self._page,
                    context=self._context,
                    action_planner=planner,
                    goal=goal,
                    options=options,
                    wait_for_human=wait_for_human,
                )
            else:
                self._agent.goal = goal

            self._initialized = True
            self.ready.emit()
            self.log.emit("Initialized. Starting steps…")

            try:
                await self._step_loop_async()
            except Exception as e:
                if _is_hitl_pause(e):
                    self.log.emit("Paused for human (HITL) [init].")
                else:
                    raise
        except Exception as e:
            self.error.emit(f"Init failed: {e!r}\n{traceback.format_exc()}")
        finally:
            self.finished.emit()

    async def _step_once_async(self) -> str:
        try:
            await self._agent.step()
            if self._agent.status == 'success':
                self.log.emit("Goal reached successfully.")
                return "success"
            return "ok"
        except Exception as e:
            if _is_hitl_pause(e):
                self.log.emit("Paused for human (HITL).")
                return "paused"
            self.error.emit(f"Step failed: {e!r}")
            return "error"

    async def _step_loop_async(self):
        if not (self._agent and self._page and self._context):
            self.error.emit("Agent/page/context not ready.")
            return
        self._running = True
        try:
            while self._running:
                try:
                    res = await self._step_once_async()
                except Exception as e:
                    if _is_hitl_pause(e):
                        self.log.emit("Paused for human (HITL) [loop].")
                        break
                    raise
                if res in ("paused", "error","success"):
                    break
                await asyncio.sleep(0.05)
        finally:
            self._running = False


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Claude + Playwright (PyQt5)")
        self.resize(820, 520)

        # === UI elements ===
        self.goal_edit = QtWidgets.QLineEdit(self)
        self.goal_edit.setPlaceholderText("Enter your goal…")
        self.goal_edit.setText("Search for MCP Wikipedia")

        # === NEW: API Key UI ===
        self.api_edit = QtWidgets.QLineEdit(self)
        self.api_edit.setPlaceholderText("Enter API Key")
        self.api_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.remember_chk = QtWidgets.QCheckBox("Remember on this device (system keychain)")
        self.apply_key_btn = QtWidgets.QPushButton("Use This Key")
        self.test_key_btn = QtWidgets.QPushButton("Test Key")
        self.forget_key_btn = QtWidgets.QPushButton("Forget Key")

        self.start_btn = QtWidgets.QPushButton("Start / Continue")
        self.resume_btn = QtWidgets.QPushButton("✅ I solved it — Resume")
        self.resume_btn.setEnabled(False)
        self.stop_btn = QtWidgets.QPushButton("Stop & Cleanup")

        self.status_lbl = QtWidgets.QLabel()
        self.status_lbl.setWordWrap(True)

        self.log_box = QtWidgets.QPlainTextEdit()
        self.log_box.setReadOnly(True)

        # === Layout ===
        layout = QtWidgets.QVBoxLayout(self)

        # Key row
        key_row = QtWidgets.QHBoxLayout()
        key_row.addWidget(self.api_edit, 2)
        key_row.addWidget(self.apply_key_btn, 0)
        key_row.addWidget(self.test_key_btn, 0)
        key_row.addWidget(self.forget_key_btn, 0)

        layout.addWidget(QtWidgets.QLabel("<b>API Key</b>"))
        layout.addLayout(key_row)
        layout.addWidget(self.remember_chk)
        layout.addSpacing(10)

        layout.addWidget(QtWidgets.QLabel("<b>Goal</b>"))
        layout.addWidget(self.goal_edit)

        ctl = QtWidgets.QHBoxLayout()
        ctl.addWidget(self.start_btn)
        ctl.addWidget(self.resume_btn)
        ctl.addWidget(self.stop_btn)
        layout.addLayout(ctl)

        layout.addWidget(self.status_lbl)
        layout.addWidget(self.log_box, 1)

        # === Worker thread wiring ===
        # 首选：环境变量；否则尝试 keyring；否则空
        initial_key = os.environ.get("apikey", "") or load_api_key_from_keyring()
        self.thread = QtCore.QThread(self)
        self.worker = Worker(initial_key)
        self.worker.moveToThread(self.thread)

        # UI → Worker
        self.start_btn.clicked.connect(self.on_start)
        self.resume_btn.clicked.connect(self.on_resume)
        self.stop_btn.clicked.connect(self.on_stop)

        self.apply_key_btn.clicked.connect(self.on_apply_key)
        self.test_key_btn.clicked.connect(self.on_test_key)
        self.forget_key_btn.clicked.connect(self.on_forget_key)

        # Worker → UI
        self.worker.log.connect(self.append_log)
        self.worker.error.connect(self.on_error)
        self.worker.hitl.connect(self.on_hitl)
        self.worker.ready.connect(self.on_ready)
        self.worker.finished.connect(self.on_finished)

        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.start()

        # 提示 key 来源（不回显环境变量）
        if os.environ.get("apikey", ""):
            self.status_lbl.setText("Using API key from environment.")
        elif initial_key:
            self.status_lbl.setText("Loaded API key from system keychain.")

        if not KEYRING_AVAILABLE:
            self.remember_chk.setEnabled(False)
            self.remember_chk.setToolTip("keyring not available on this system.")
            self.forget_key_btn.setEnabled(False)

    # ---------- UI handlers ----------
    def append_log(self, text: str):
        self.log_box.appendPlainText(text)

    def on_ready(self):
        self.status_lbl.setText("Initialized.")
        self.append_log("Ready.")

    def on_error(self, msg: str):
        self.status_lbl.setText(f"<span style='color:#b00'>ERROR: {msg}</span>")
        self.append_log(msg)
        self.resume_btn.setEnabled(False)
        self.start_btn.setEnabled(True)

    def on_hitl(self, msg: str):
        self.status_lbl.setText(f"<b>HITL:</b> {msg}")
        self.append_log(f"HITL: {msg}")
        self.resume_btn.setEnabled(True)
        self.start_btn.setEnabled(False)

    def on_finished(self):
        pass

    def on_start(self):
        goal = self.goal_edit.text().strip()
        QtCore.QMetaObject.invokeMethod(self.worker, "set_goal",
                                        QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(str, goal))
        QtCore.QMetaObject.invokeMethod(self.worker, "run", QtCore.Qt.QueuedConnection)
        self.status_lbl.setText("Running…")
        self.append_log("Worker started/continued.")
        self.resume_btn.setEnabled(False)
        self.start_btn.setEnabled(False)

    def on_resume(self):
        QtCore.QMetaObject.invokeMethod(self.worker, "run", QtCore.Qt.QueuedConnection)
        self.status_lbl.setText("Resuming…")
        self.append_log("Resuming after HITL.")
        self.resume_btn.setEnabled(False)
        self.start_btn.setEnabled(False)

    def on_stop(self):
        QtCore.QMetaObject.invokeMethod(self.worker, "shutdown", QtCore.Qt.QueuedConnection)
        self.status_lbl.setText("Stopped and cleaned up.")
        self.append_log("Stopped.")
        self.resume_btn.setEnabled(False)
        self.start_btn.setEnabled(True)

    # === NEW: API key operations ===
    def on_apply_key(self):
        # 优先使用输入框；若为空则尝试 keyring；环境变量无需设置（已在启动时用上）
        entered = self.api_edit.text().strip()
        key = entered or load_api_key_from_keyring() or ""
        if not key and not os.environ.get("apikey", ""):
            self.status_lbl.setText("No API key provided.")
            return

        if entered:
            # 仅当用户输入了新 key，才传给 Worker
            QtCore.QMetaObject.invokeMethod(self.worker, "set_api_key",
                                            QtCore.Qt.QueuedConnection,
                                            QtCore.Q_ARG(str, key))

            if self.remember_chk.isChecked() and not os.environ.get("apikey", ""):
                if save_api_key_to_keyring(key):
                    self.status_lbl.setText("Key saved to system keychain.")
                else:
                    self.status_lbl.setText("Failed to save key to keychain.")
            else:
                self.status_lbl.setText("Key set for this session.")
        else:
            # 未输入：若环境变量或 keyring 已有，则提示
            if os.environ.get("apikey", ""):
                self.status_lbl.setText("Using API key from environment.")
            elif key:
                # 将 keyring 中的 key 设给 Worker（内存）
                QtCore.QMetaObject.invokeMethod(self.worker, "set_api_key",
                                                QtCore.Qt.QueuedConnection,
                                                QtCore.Q_ARG(str, key))
                self.status_lbl.setText("Key loaded from keychain for this session.")
            else:
                self.status_lbl.setText("No API key available.")

    def on_test_key(self):
        # 仅做轻量本地格式校验；如需可调用最小探针 API
        entered = self.api_edit.text().strip()
        key = entered or os.environ.get("apikey", "") or load_api_key_from_keyring()
        if not key:
            self.status_lbl.setText("No API key to test.")
            return
        if key.startswith("sk-") or len(key) >= 20:
            self.status_lbl.setText("Key looks OK.")
        else:
            self.status_lbl.setText("Key format looks invalid.")

    def on_forget_key(self):
        if delete_api_key_from_keyring():
            self.status_lbl.setText("Key removed from system keychain.")
        else:
            self.status_lbl.setText("No key in keychain or keyring unavailable.")

    def closeEvent(self, event):
        try:
            self.on_stop()
        except Exception:
            pass
        self.thread.quit()
        self.thread.wait(2000)
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

ensure_playwright_browsers_blocking()
if __name__ == "__main__":
    main()
