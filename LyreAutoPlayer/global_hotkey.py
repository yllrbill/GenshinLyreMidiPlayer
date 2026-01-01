#!/usr/bin/env python3
"""
Windows 全局热键模块 - 使用 RegisterHotKey API

RegisterHotKey 是 Windows 原生 API，注册的热键：
- 系统级别，游戏无法阻止
- 不需要 hook，不会被反作弊检测

关键设计：
- 所有 RegisterHotKey 调用必须在消息循环线程中执行
- 使用队列传递注册请求到消息循环线程
"""
import ctypes
import ctypes.wintypes as wintypes
import threading
import queue
from typing import Callable, Dict, Optional, Tuple
import atexit

# Windows API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 消息常量
WM_HOTKEY = 0x0312
WM_USER = 0x0400
WM_QUIT = 0x0012

# 修饰键
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # 防止按住重复触发

# 虚拟键码映射
VK_MAP = {
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'f13': 0x7C, 'f14': 0x7D, 'f15': 0x7E, 'f16': 0x7F,
    'pause': 0x13, 'scroll': 0x91, 'print': 0x2C,
    'insert': 0x2D, 'delete': 0x2E, 'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'pagedown': 0x22,
    'num0': 0x60, 'num1': 0x61, 'num2': 0x62, 'num3': 0x63,
    'num4': 0x64, 'num5': 0x65, 'num6': 0x66, 'num7': 0x67,
    'num8': 0x68, 'num9': 0x69,
}


class GlobalHotkeyManager:
    """
    Windows 全局热键管理器 - 使用 RegisterHotKey API
    """

    def __init__(self):
        self._callbacks: Dict[int, Callable] = {}  # hotkey_id -> callback
        self._pending: list = []  # (key_str, callback) 待注册列表
        self._next_id = 1
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._ready = threading.Event()
        self._lock = threading.Lock()

        atexit.register(self.stop)

    def _parse_hotkey(self, key_str: str) -> Tuple[int, int]:
        """解析热键字符串，返回 (modifiers, vk_code)"""
        parts = key_str.lower().replace(' ', '').split('+')
        modifiers = MOD_NOREPEAT
        vk_code = 0

        for part in parts:
            if part in ('ctrl', 'control'):
                modifiers |= MOD_CONTROL
            elif part == 'alt':
                modifiers |= MOD_ALT
            elif part == 'shift':
                modifiers |= MOD_SHIFT
            elif part in ('win', 'windows'):
                modifiers |= MOD_WIN
            elif part in VK_MAP:
                vk_code = VK_MAP[part]
            else:
                raise ValueError(f"Unknown key: {part}")

        if vk_code == 0:
            raise ValueError(f"No valid key found in: {key_str}")

        return modifiers, vk_code

    def register(self, key: str, callback: Callable) -> int:
        """注册全局热键（在 start() 之前调用）"""
        modifiers, vk_code = self._parse_hotkey(key)

        with self._lock:
            hotkey_id = self._next_id
            self._next_id += 1
            self._pending.append((hotkey_id, modifiers, vk_code, callback))

        return hotkey_id

    def _message_loop(self):
        """消息循环线程 - 所有热键注册和消息处理都在这里"""
        # 创建消息队列（通过调用 PeekMessage）
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        # 注册所有待注册的热键
        with self._lock:
            for hotkey_id, modifiers, vk_code, callback in self._pending:
                result = user32.RegisterHotKey(None, hotkey_id, modifiers, vk_code)
                if result:
                    self._callbacks[hotkey_id] = callback
                else:
                    error = kernel32.GetLastError()
                    print(f"[GlobalHotkey] RegisterHotKey failed for id={hotkey_id}: error {error}")
            self._pending.clear()

        # 通知主线程准备就绪
        self._ready.set()

        # 消息循环
        while self._running:
            # GetMessage 会阻塞直到收到消息，比 PeekMessage+Sleep 更高效
            # 但我们需要能够退出，所以用 timeout 版本
            result = user32.MsgWaitForMultipleObjects(
                0, None, False, 100,  # 100ms timeout
                0x04FF  # QS_ALLINPUT
            )

            # 处理所有待处理消息
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):  # PM_REMOVE = 1
                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    callback = self._callbacks.get(hotkey_id)
                    if callback:
                        try:
                            callback()
                        except Exception as e:
                            print(f"[GlobalHotkey] Callback error: {e}")
                elif msg.message == WM_QUIT:
                    self._running = False
                    break

        # 清理：取消所有热键注册
        for hotkey_id in self._callbacks:
            user32.UnregisterHotKey(None, hotkey_id)
        self._callbacks.clear()

    def start(self):
        """启动热键监听"""
        if self._running:
            return

        self._running = True
        self._ready.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

        # 等待线程准备就绪
        self._ready.wait(timeout=2.0)

    def stop(self):
        """停止热键监听"""
        if not self._running:
            return

        self._running = False

        # 发送 WM_QUIT 消息让线程退出阻塞
        if self._thread and self._thread.is_alive():
            # 可以使用 PostThreadMessage，但由于 daemon=True，直接等待即可
            self._thread.join(timeout=1.0)

        self._thread = None


# 便捷接口
_manager: Optional[GlobalHotkeyManager] = None

def get_manager() -> GlobalHotkeyManager:
    global _manager
    if _manager is None:
        _manager = GlobalHotkeyManager()
    return _manager

def register_hotkey(key: str, callback: Callable) -> int:
    mgr = get_manager()
    hotkey_id = mgr.register(key, callback)
    if not mgr._running:
        mgr.start()
    return hotkey_id

def stop_all():
    global _manager
    if _manager:
        _manager.stop()
        _manager = None


if __name__ == "__main__":
    import time

    print("=" * 50)
    print("全局热键测试 (RegisterHotKey API)")
    print("按 F5/F6 测试 (在任何窗口都有效)")
    print("按 Ctrl+C 退出")
    print("=" * 50)

    received = []

    def on_f5():
        received.append('F5')
        print("★ F5 pressed!")

    def on_f6():
        received.append('F6')
        print("★ F6 pressed!")

    mgr = GlobalHotkeyManager()
    mgr.register('f5', on_f5)
    mgr.register('f6', on_f6)
    mgr.start()

    print("\nWaiting for hotkeys...")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\nReceived: {received}")
    finally:
        mgr.stop()
