"""
Input Manager v2 - 增强版输入系统核心模块

核心改进：
1. 使用 SendInput + 扫描码，解决 DirectX 游戏不触发问题
2. 状态机正确：KeyDown/KeyUp 一一对应
3. 异常安全：窗口失焦/崩溃时自动释放所有按键
4. 长按真实生效：按下保持、松开结束
5. 诊断能力：实时状态、延迟统计、丢事件检测

Author: LyreAutoPlayer Refactor v2
"""

import time
import ctypes
import threading
import atexit
from dataclasses import dataclass, field
from typing import Set, Dict, Deque, Optional, List, Tuple, Callable
from collections import deque
from enum import Enum

# ============== Windows API 定义 ==============

# Windows 常量
INPUT_KEYBOARD = 1
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008  # 关键：使用扫描码而非虚拟键码
KEYEVENTF_EXTENDEDKEY = 0x0001

# MapVirtualKey 参数
MAPVK_VK_TO_VSC = 0
MAPVK_VK_TO_VSC_EX = 4  # 返回扫描码，高位标记扩展键

# 扩展键 VK 列表 (需要 KEYEVENTF_EXTENDEDKEY 标志)
# 参考: https://learn.microsoft.com/en-us/windows/win32/inputdev/about-keyboard-input
EXTENDED_KEY_VKS = frozenset([
    0x21,  # VK_PRIOR (Page Up)
    0x22,  # VK_NEXT (Page Down)
    0x23,  # VK_END
    0x24,  # VK_HOME
    0x25,  # VK_LEFT
    0x26,  # VK_UP
    0x27,  # VK_RIGHT
    0x28,  # VK_DOWN
    0x2D,  # VK_INSERT
    0x2E,  # VK_DELETE
    0x5B,  # VK_LWIN
    0x5C,  # VK_RWIN
    0x5D,  # VK_APPS
    0x6F,  # VK_DIVIDE (Numpad /)
    0x90,  # VK_NUMLOCK
    0xA3,  # VK_RCONTROL
    0xA5,  # VK_RMENU (Right Alt)
])


def is_extended_key(vk_code: int) -> bool:
    """判断虚拟键码是否为扩展键"""
    return vk_code in EXTENDED_KEY_VKS


# ctypes 结构体
# 注意: INPUT_UNION 必须包含所有成员以获得正确的 union 大小 (40 bytes on 64-bit)
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]

# Windows API 函数
user32 = ctypes.windll.user32
SendInput = user32.SendInput
MapVirtualKeyW = user32.MapVirtualKeyW
GetAsyncKeyState = user32.GetAsyncKeyState
GetForegroundWindow = user32.GetForegroundWindow

# IME 相关 API (用于禁用输入法，防止时间戳快捷输入)
try:
    imm32 = ctypes.windll.imm32
    ImmGetContext = imm32.ImmGetContext
    ImmReleaseContext = imm32.ImmReleaseContext
    ImmAssociateContextEx = imm32.ImmAssociateContextEx
    ImmGetDefaultIMEWnd = imm32.ImmGetDefaultIMEWnd
    # IACE_IGNORENOCONTEXT = 0x0001
    # IACE_DEFAULT = 0x0010
    IACE_CHILDREN = 0x0001
    _IME_AVAILABLE = True
except Exception:
    _IME_AVAILABLE = False
    ImmGetContext = None
    ImmReleaseContext = None
    ImmAssociateContextEx = None
    ImmGetDefaultIMEWnd = None
    IACE_CHILDREN = 0x0001


def disable_ime_for_window(hwnd: int) -> bool:
    """
    禁用指定窗口的 IME 输入法。

    用于防止中文输入法的快捷键（如 'rq' = 日期，'sj' = 时间）被触发。

    Args:
        hwnd: 目标窗口句柄

    Returns:
        True 如果成功禁用，False 如果失败或 IME API 不可用
    """
    if not _IME_AVAILABLE or hwnd is None or hwnd == 0:
        return False

    try:
        # 方法1: 取消 IME 上下文关联
        # ImmAssociateContextEx(hwnd, NULL, IACE_CHILDREN) 会禁用窗口及其子窗口的 IME
        result = ImmAssociateContextEx(hwnd, None, IACE_CHILDREN)
        return result != 0
    except Exception:
        return False


def enable_ime_for_window(hwnd: int) -> bool:
    """
    恢复指定窗口的 IME 输入法。

    Args:
        hwnd: 目标窗口句柄

    Returns:
        True 如果成功恢复，False 如果失败或 IME API 不可用
    """
    if not _IME_AVAILABLE or hwnd is None or hwnd == 0:
        return False

    try:
        # 恢复默认 IME 上下文
        # IACE_DEFAULT = 0x0010
        IACE_DEFAULT = 0x0010
        result = ImmAssociateContextEx(hwnd, None, IACE_DEFAULT)
        return result != 0
    except Exception:
        return False

# ============== 虚拟键码映射 ==============

# 字符到虚拟键码的映射
VK_CODES: Dict[str, int] = {
    # 字母键
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47,
    'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E,
    'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55,
    'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
    # 数字键
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    # 符号键
    ',': 0xBC,  # VK_OEM_COMMA
    '.': 0xBE,  # VK_OEM_PERIOD
    '/': 0xBF,  # VK_OEM_2
    ';': 0xBA,  # VK_OEM_1
    ':': 0xBA,  # VK_OEM_1 (same key as ';', used in 36-key mode)
    '[': 0xDB,  # VK_OEM_4
    ']': 0xDD,  # VK_OEM_6
    '-': 0xBD,  # VK_OEM_MINUS
    '=': 0xBB,  # VK_OEM_PLUS
    '`': 0xC0,  # VK_OEM_3
    '\'': 0xDE, # VK_OEM_7
    '\\': 0xDC, # VK_OEM_5
    # 功能键
    'space': 0x20,
    'enter': 0x0D,
    'tab': 0x09,
    'backspace': 0x08,
    'escape': 0x1B,
    'shift': 0x10,
    'ctrl': 0x11,
    'alt': 0x12,
}

def get_vk_code(key: str) -> Optional[int]:
    """获取按键的虚拟键码"""
    key = key.lower()
    return VK_CODES.get(key)

def get_scan_code(vk_code: int) -> int:
    """获取虚拟键码对应的扫描码"""
    return MapVirtualKeyW(vk_code, MAPVK_VK_TO_VSC)


# ============== 事件类型 ==============

class InputEventType(Enum):
    PRESS = "press"
    RELEASE = "release"
    RELEASE_ALL = "release_all"
    FOCUS_LOST = "focus_lost"
    STUCK_RECOVERY = "stuck_recovery"


@dataclass
class InputEvent:
    """单个输入事件记录"""
    timestamp: float          # perf_counter 时间
    event_type: InputEventType
    key: str
    success: bool
    latency_ms: float = 0.0   # 调度延迟
    note: Optional[int] = None  # 对应MIDI音符(可选)
    vk_code: int = 0
    scan_code: int = 0


@dataclass
class InputStats:
    """输入统计"""
    total_press: int = 0
    total_release: int = 0
    failed_press: int = 0
    failed_release: int = 0
    stuck_key_recoveries: int = 0
    focus_lost_releases: int = 0
    max_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    chord_count: int = 0          # 和弦计数
    max_simultaneous_keys: int = 0  # 最大同时按下数

    # 延迟分布
    latency_buckets: Dict[str, int] = field(default_factory=lambda: {
        "<1ms": 0, "1-2ms": 0, "2-5ms": 0, "5-10ms": 0, ">10ms": 0
    })

    def record_latency(self, latency_ms: float):
        # 滑动平均
        self.avg_latency_ms = (self.avg_latency_ms * 0.9) + (latency_ms * 0.1)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        # 分布统计
        if latency_ms < 1:
            self.latency_buckets["<1ms"] += 1
        elif latency_ms < 2:
            self.latency_buckets["1-2ms"] += 1
        elif latency_ms < 5:
            self.latency_buckets["2-5ms"] += 1
        elif latency_ms < 10:
            self.latency_buckets["5-10ms"] += 1
        else:
            self.latency_buckets[">10ms"] += 1

    def reset(self):
        self.total_press = 0
        self.total_release = 0
        self.failed_press = 0
        self.failed_release = 0
        self.stuck_key_recoveries = 0
        self.focus_lost_releases = 0
        self.max_latency_ms = 0.0
        self.avg_latency_ms = 0.0
        self.chord_count = 0
        self.max_simultaneous_keys = 0
        self.latency_buckets = {
            "<1ms": 0, "1-2ms": 0, "2-5ms": 0, "5-10ms": 0, ">10ms": 0
        }


@dataclass
class InputManagerConfig:
    """输入管理器配置"""
    backend: str = "sendinput"  # sendinput (推荐), pydirectinput, keyboard, debug

    # 可靠性设置
    min_press_interval_ms: float = 2.0   # 同一键的最小按压间隔（防抖）
    min_key_hold_ms: float = 8.0         # 最小按键保持时间（确保游戏检测到）
    key_timeout_ms: float = 30000.0      # 按键超时（30秒自动释放）

    # 监控设置
    enable_focus_monitor: bool = True    # 启用窗口焦点监控
    focus_check_interval_ms: float = 100.0  # 焦点检查间隔
    target_hwnd: Optional[int] = None    # 目标窗口句柄

    # 诊断设置
    enable_diagnostics: bool = False
    log_buffer_size: int = 200

    # 安全设置
    auto_release_on_stop: bool = True
    check_stuck_interval_ms: float = 1000.0


# ============== 输入后端 ==============

class InputBackend:
    """输入后端抽象基类"""

    def key_down(self, key: str, vk_code: int, scan_code: int) -> bool:
        raise NotImplementedError

    def key_up(self, key: str, vk_code: int, scan_code: int) -> bool:
        raise NotImplementedError

    def get_name(self) -> str:
        return self.__class__.__name__


class SendInputBackend(InputBackend):
    """
    SendInput 后端 - 使用扫描码，兼容 DirectX 游戏

    这是推荐的后端，因为：
    1. 使用 KEYEVENTF_SCANCODE 标志，DirectInput 游戏可以接收
    2. 使用 SendInput API，比 keybd_event 更可靠
    3. 直接操作，无额外延迟
    """

    def __init__(self):
        self._extra = ctypes.pointer(ctypes.c_ulong(0))

    def _send_key(self, vk_code: int, scan_code: int, key_up: bool) -> bool:
        """发送按键事件"""
        if scan_code == 0:
            # 如果没有扫描码，从虚拟键码获取
            scan_code = get_scan_code(vk_code)

        flags = KEYEVENTF_SCANCODE
        if key_up:
            flags |= KEYEVENTF_KEYUP

        # 检查是否是扩展键（如方向键、Insert/Delete、右Ctrl/Alt等）
        # 扩展键需要设置 KEYEVENTF_EXTENDEDKEY 标志
        if is_extended_key(vk_code):
            flags |= KEYEVENTF_EXTENDEDKEY

        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki.wVk = 0  # 使用扫描码时不需要虚拟键码
        inp.union.ki.wScan = scan_code
        inp.union.ki.dwFlags = flags
        inp.union.ki.time = 0
        inp.union.ki.dwExtraInfo = self._extra

        result = SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        return result == 1

    def key_down(self, key: str, vk_code: int, scan_code: int) -> bool:
        return self._send_key(vk_code, scan_code, key_up=False)

    def key_up(self, key: str, vk_code: int, scan_code: int) -> bool:
        return self._send_key(vk_code, scan_code, key_up=True)

    def get_name(self) -> str:
        return "SendInput (scancode)"


class PyDirectInputBackend(InputBackend):
    """pydirectinput 后端（备选）"""

    def __init__(self):
        import pydirectinput
        pydirectinput.PAUSE = 0
        pydirectinput.FAILSAFE = False
        self._pdi = pydirectinput

    def key_down(self, key: str, vk_code: int, scan_code: int) -> bool:
        try:
            self._pdi.keyDown(key)
            return True
        except Exception:
            return False

    def key_up(self, key: str, vk_code: int, scan_code: int) -> bool:
        try:
            self._pdi.keyUp(key)
            return True
        except Exception:
            return False

    def get_name(self) -> str:
        return "pydirectinput"


class KeyboardLibBackend(InputBackend):
    """keyboard 库后端（备选）"""

    def __init__(self):
        import keyboard
        self._kb = keyboard

    def key_down(self, key: str, vk_code: int, scan_code: int) -> bool:
        try:
            self._kb.press(key)
            return True
        except Exception:
            return False

    def key_up(self, key: str, vk_code: int, scan_code: int) -> bool:
        try:
            self._kb.release(key)
            return True
        except Exception:
            return False

    def get_name(self) -> str:
        return "keyboard"


class DebugBackend(InputBackend):
    """调试后端（只记录不发送）"""

    def __init__(self):
        self.log: List[Tuple[float, str, bool, int, int]] = []

    def key_down(self, key: str, vk_code: int, scan_code: int) -> bool:
        self.log.append((time.perf_counter(), key, True, vk_code, scan_code))
        return True

    def key_up(self, key: str, vk_code: int, scan_code: int) -> bool:
        self.log.append((time.perf_counter(), key, False, vk_code, scan_code))
        return True

    def get_name(self) -> str:
        return "debug"

    def clear_log(self):
        self.log.clear()

    def get_log_summary(self) -> str:
        """获取日志摘要"""
        if not self.log:
            return "No events logged"

        lines = []
        for ts, key, is_down, vk, sc in self.log[-20:]:
            action = "DOWN" if is_down else "UP"
            lines.append(f"{ts:.4f}: {key} {action} (VK=0x{vk:02X}, SC=0x{sc:02X})")
        return "\n".join(lines)


# ============== InputManager ==============

class InputManager:
    """
    输入管理器 v2 - 单一事实来源

    核心职责:
    1. 管理所有按键状态 (active_keys)
    2. 保证 keyDown/keyUp 一一对应
    3. 异常时安全释放所有按键（窗口失焦、超时、停止）
    4. 提供诊断能力

    关键改进:
    - 使用 SendInput + 扫描码，兼容 DirectX 游戏
    - 线程安全的状态管理
    - 自动窗口焦点监控
    """

    # 全局实例追踪，用于 atexit 清理
    _instances: List['InputManager'] = []
    _atexit_registered = False

    def __init__(self, config: InputManagerConfig = None):
        self.config = config or InputManagerConfig()

        # 线程锁
        self._lock = threading.RLock()

        # 状态
        self._active_keys: Dict[str, float] = {}  # key -> press_time
        self._key_codes: Dict[str, Tuple[int, int]] = {}  # key -> (vk_code, scan_code)
        self._last_key_time: Dict[str, float] = {}  # 防抖用

        # 诊断
        self._event_log: Deque[InputEvent] = deque(maxlen=self.config.log_buffer_size)
        self._stats = InputStats()

        # 后端
        self._backend = self._create_backend(self.config.backend)

        # 时钟
        self._clock = time.perf_counter

        # 焦点监控
        self._focus_thread: Optional[threading.Thread] = None
        self._focus_stop = threading.Event()
        self._last_focus_hwnd: Optional[int] = None

        # 注册全局实例
        InputManager._instances.append(self)
        if not InputManager._atexit_registered:
            atexit.register(InputManager._cleanup_all)
            InputManager._atexit_registered = True

        # 启动焦点监控
        if self.config.enable_focus_monitor:
            self._start_focus_monitor()

    @staticmethod
    def _cleanup_all():
        """atexit 钩子：清理所有实例"""
        for instance in InputManager._instances:
            try:
                instance.release_all()
                instance.stop()
            except Exception:
                pass

    def _create_backend(self, backend_name: str) -> InputBackend:
        if backend_name == "sendinput":
            return SendInputBackend()
        elif backend_name == "pydirectinput":
            return PyDirectInputBackend()
        elif backend_name == "keyboard":
            return KeyboardLibBackend()
        elif backend_name == "debug":
            return DebugBackend()
        else:
            return SendInputBackend()  # 默认使用 SendInput

    def _start_focus_monitor(self):
        """启动窗口焦点监控线程"""
        if self._focus_thread is not None:
            return

        self._focus_stop.clear()
        self._focus_thread = threading.Thread(target=self._focus_monitor_loop, daemon=True)
        self._focus_thread.start()

    def _focus_monitor_loop(self):
        """焦点监控循环"""
        interval = self.config.focus_check_interval_ms / 1000.0

        while not self._focus_stop.is_set():
            try:
                current_hwnd = GetForegroundWindow()

                # 如果设置了目标窗口，检查焦点是否离开
                if self.config.target_hwnd is not None:
                    if self._last_focus_hwnd == self.config.target_hwnd and current_hwnd != self.config.target_hwnd:
                        # 焦点离开目标窗口，释放所有按键
                        with self._lock:
                            if self._active_keys:
                                count = len(self._active_keys)
                                self._release_all_internal(reason=InputEventType.FOCUS_LOST)
                                self._stats.focus_lost_releases += count

                self._last_focus_hwnd = current_hwnd

                # 同时检查超时按键
                self._check_stuck_keys_internal()

            except Exception:
                pass

            self._focus_stop.wait(interval)

    def _check_stuck_keys_internal(self):
        """内部检查超时按键（不加锁）"""
        now = self._clock()
        timeout_s = self.config.key_timeout_ms / 1000.0

        with self._lock:
            stuck_keys = []
            for key, press_time in list(self._active_keys.items()):
                if now - press_time > timeout_s:
                    stuck_keys.append(key)

            for key in stuck_keys:
                self._release_key_internal(key, reason=InputEventType.STUCK_RECOVERY)
                self._stats.stuck_key_recoveries += 1

    def set_target_window(self, hwnd: Optional[int]):
        """设置目标窗口句柄"""
        self.config.target_hwnd = hwnd

    def stop(self):
        """停止输入管理器"""
        # 停止焦点监控
        self._focus_stop.set()
        if self._focus_thread is not None:
            self._focus_thread.join(timeout=1.0)
            self._focus_thread = None

        # 释放所有按键
        self.release_all()

        # 从全局实例中移除
        if self in InputManager._instances:
            InputManager._instances.remove(self)

    def press(self, key: str, note: Optional[int] = None) -> bool:
        """
        按下按键

        Returns:
            True 如果成功按下（或已经按下）
            False 如果发送失败
        """
        key = key.lower()
        now = self._clock()

        with self._lock:
            # 防抖：检查距离上次按键的间隔
            if key in self._last_key_time:
                interval_ms = (now - self._last_key_time[key]) * 1000
                if interval_ms < self.config.min_press_interval_ms:
                    # 间隔太短，跳过但不算失败
                    return True

            # 如果已经按下，不重复发送
            if key in self._active_keys:
                return True

            # 获取键码
            vk_code = get_vk_code(key)
            if vk_code is None:
                # 未知按键
                self._stats.failed_press += 1
                return False

            scan_code = get_scan_code(vk_code)

            # 发送按键
            scheduled_time = now
            success = self._backend.key_down(key, vk_code, scan_code)
            actual_time = self._clock()
            latency_ms = (actual_time - scheduled_time) * 1000

            if success:
                self._active_keys[key] = now
                self._key_codes[key] = (vk_code, scan_code)
                self._stats.total_press += 1

                # 更新最大同时按键数
                current_count = len(self._active_keys)
                if current_count > self._stats.max_simultaneous_keys:
                    self._stats.max_simultaneous_keys = current_count
                if current_count > 1:
                    self._stats.chord_count += 1
            else:
                self._stats.failed_press += 1

            self._last_key_time[key] = now
            self._stats.record_latency(latency_ms)

            # 记录事件
            if self.config.enable_diagnostics:
                self._log_event(InputEvent(
                    timestamp=now,
                    event_type=InputEventType.PRESS,
                    key=key,
                    success=success,
                    latency_ms=latency_ms,
                    note=note,
                    vk_code=vk_code,
                    scan_code=scan_code
                ))

            return success

    def release(self, key: str, note: Optional[int] = None) -> bool:
        """
        释放按键

        Returns:
            True 如果成功释放（或本就未按下）
            False 如果发送失败
        """
        with self._lock:
            return self._release_key_internal(key, note=note)

    def _release_key_internal(self, key: str, note: Optional[int] = None,
                               reason: InputEventType = InputEventType.RELEASE) -> bool:
        """内部释放按键（需要已持有锁）"""
        key = key.lower()
        now = self._clock()

        # 如果未按下，直接返回成功（幂等）
        if key not in self._active_keys:
            return True

        # 获取键码
        vk_code, scan_code = self._key_codes.get(key, (0, 0))
        if vk_code == 0:
            vk_code = get_vk_code(key) or 0
            scan_code = get_scan_code(vk_code) if vk_code else 0

        # 检查最小保持时间
        press_time = self._active_keys.get(key, now)
        hold_time_ms = (now - press_time) * 1000
        if hold_time_ms < self.config.min_key_hold_ms:
            # 等待达到最小保持时间
            wait_ms = self.config.min_key_hold_ms - hold_time_ms
            time.sleep(wait_ms / 1000.0)
            now = self._clock()

        # 发送释放
        success = self._backend.key_up(key, vk_code, scan_code)
        latency_ms = (self._clock() - now) * 1000

        if success:
            del self._active_keys[key]
            self._key_codes.pop(key, None)
            self._stats.total_release += 1
        else:
            self._stats.failed_release += 1

        self._stats.record_latency(latency_ms)

        if self.config.enable_diagnostics:
            self._log_event(InputEvent(
                timestamp=now,
                event_type=reason,
                key=key,
                success=success,
                latency_ms=latency_ms,
                note=note,
                vk_code=vk_code,
                scan_code=scan_code
            ))

        return success

    def release_all(self) -> int:
        """
        释放所有按下的键

        Returns:
            释放的按键数量
        """
        with self._lock:
            return self._release_all_internal()

    def _release_all_internal(self, reason: InputEventType = InputEventType.RELEASE_ALL) -> int:
        """内部释放所有按键（需要已持有锁）"""
        keys_to_release = list(self._active_keys.keys())
        released = 0

        for key in keys_to_release:
            if self._release_key_internal(key, reason=reason):
                released += 1

        if self.config.enable_diagnostics and released > 0:
            self._log_event(InputEvent(
                timestamp=self._clock(),
                event_type=reason,
                key=f"[{released} keys]",
                success=True,
                latency_ms=0
            ))

        return released

    def is_pressed(self, key: str) -> bool:
        with self._lock:
            return key.lower() in self._active_keys

    def get_active_keys(self) -> Set[str]:
        with self._lock:
            return set(self._active_keys.keys())

    def get_active_count(self) -> int:
        with self._lock:
            return len(self._active_keys)

    def get_press_duration(self, key: str) -> Optional[float]:
        """获取按键已按下的时长（秒）"""
        key = key.lower()
        with self._lock:
            if key in self._active_keys:
                return self._clock() - self._active_keys[key]
        return None

    def check_stuck_keys(self) -> List[str]:
        """检测并释放超时的卡键"""
        now = self._clock()
        stuck = []
        timeout_s = self.config.key_timeout_ms / 1000.0

        with self._lock:
            for key, press_time in list(self._active_keys.items()):
                if now - press_time > timeout_s:
                    stuck.append(key)
                    self._release_key_internal(key, reason=InputEventType.STUCK_RECOVERY)
                    self._stats.stuck_key_recoveries += 1

        return stuck

    def get_diagnostics(self) -> Dict:
        """获取诊断信息"""
        with self._lock:
            # 计算当前按键的持续时间
            now = self._clock()
            key_durations = {}
            for key, press_time in self._active_keys.items():
                key_durations[key] = round((now - press_time) * 1000, 1)  # ms

            return {
                "backend": self._backend.get_name(),
                "active_keys": sorted(list(self._active_keys.keys())),
                "active_count": len(self._active_keys),
                "key_durations_ms": key_durations,
                "focus_monitoring": self.config.enable_focus_monitor,
                "target_hwnd": self.config.target_hwnd,
                "current_hwnd": self._last_focus_hwnd,
                "stats": {
                    "total_press": self._stats.total_press,
                    "total_release": self._stats.total_release,
                    "failed_press": self._stats.failed_press,
                    "failed_release": self._stats.failed_release,
                    "stuck_recoveries": self._stats.stuck_key_recoveries,
                    "focus_lost_releases": self._stats.focus_lost_releases,
                    "max_latency_ms": round(self._stats.max_latency_ms, 2),
                    "avg_latency_ms": round(self._stats.avg_latency_ms, 2),
                    "max_simultaneous": self._stats.max_simultaneous_keys,
                    "chord_count": self._stats.chord_count,
                    "latency_distribution": dict(self._stats.latency_buckets),
                },
                "recent_events": [
                    {
                        "time": round(e.timestamp, 4),
                        "type": e.event_type.value,
                        "key": e.key,
                        "ok": e.success,
                        "latency": round(e.latency_ms, 2),
                        "vk": f"0x{e.vk_code:02X}" if e.vk_code else None,
                        "sc": f"0x{e.scan_code:02X}" if e.scan_code else None,
                    }
                    for e in list(self._event_log)[-10:]
                ]
            }

    def get_stats(self) -> InputStats:
        return self._stats

    def reset_stats(self):
        """重置统计数据"""
        with self._lock:
            self._stats.reset()
            self._event_log.clear()

    def _log_event(self, event: InputEvent):
        self._event_log.append(event)

    def get_status_line(self) -> str:
        """获取单行状态摘要，用于实时显示"""
        with self._lock:
            active = ",".join(sorted(self._active_keys.keys())) or "(none)"
            return f"Keys: [{active}] | Press: {self._stats.total_press} | Fail: {self._stats.failed_press} | Lat: {self._stats.avg_latency_ms:.1f}ms"


# ============== 工厂函数 ==============

def create_input_manager(
    enable_diagnostics: bool = False,
    backend: str = "sendinput",
    target_hwnd: Optional[int] = None,
    enable_focus_monitor: bool = True
) -> InputManager:
    """便捷工厂函数"""
    config = InputManagerConfig(
        backend=backend,
        enable_diagnostics=enable_diagnostics,
        target_hwnd=target_hwnd,
        enable_focus_monitor=enable_focus_monitor
    )
    return InputManager(config)


# ============== 自测试 ==============

def self_test():
    """自测试函数"""
    print("=== InputManager v2 Self-Test ===\n")

    # 使用 debug 后端测试
    config = InputManagerConfig(
        backend="debug",
        enable_diagnostics=True,
        enable_focus_monitor=False  # 测试时不需要
    )
    mgr = InputManager(config)

    print(f"Backend: {mgr._backend.get_name()}")
    print(f"VK codes loaded: {len(VK_CODES)} keys")

    # 测试基本操作
    print("\n--- Basic Press/Release ---")
    assert mgr.press('a'), "Press 'a' should succeed"
    assert mgr.is_pressed('a'), "'a' should be pressed"
    assert mgr.get_active_count() == 1, "Should have 1 active key"

    assert mgr.release('a'), "Release 'a' should succeed"
    assert not mgr.is_pressed('a'), "'a' should not be pressed"
    assert mgr.get_active_count() == 0, "Should have 0 active keys"
    print("Basic press/release: OK")

    # 测试和弦
    print("\n--- Chord Test ---")
    mgr.press('c')
    mgr.press('e')
    mgr.press('g')
    assert mgr.get_active_count() == 3, "Should have 3 active keys"
    print(f"Active keys: {mgr.get_active_keys()}")

    released = mgr.release_all()
    assert released == 3, f"Should release 3 keys, got {released}"
    assert mgr.get_active_count() == 0, "Should have 0 active keys after release_all"
    print("Chord test: OK")

    # 测试防抖
    print("\n--- Debounce Test ---")
    mgr.press('a')
    result = mgr.press('a')  # 应该因为防抖而返回 True 但不重复发送
    assert result, "Debounced press should return True"
    mgr.release('a')
    print("Debounce test: OK")

    # 显示诊断信息
    print("\n--- Diagnostics ---")
    diag = mgr.get_diagnostics()
    print(f"Stats: {diag['stats']}")

    # 显示 debug 后端日志
    if isinstance(mgr._backend, DebugBackend):
        print(f"\nDebug log:\n{mgr._backend.get_log_summary()}")

    mgr.stop()
    print("\n=== Self-Test PASSED ===")


if __name__ == "__main__":
    self_test()
