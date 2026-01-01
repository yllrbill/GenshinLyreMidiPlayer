"""
诊断输入系统问题
检查：1) 权限 2) SendInput 实际效果 3) 目标窗口
"""
import ctypes
import sys
import time

def is_admin():
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_foreground_window_info():
    """获取当前前台窗口信息"""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()

    # 获取窗口标题
    length = user32.GetWindowTextLengthW(hwnd) + 1
    buffer = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buffer, length)
    title = buffer.value

    # 获取进程 ID
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    return hwnd, title, pid.value

def check_process_elevation(pid):
    """检查进程是否以管理员权限运行"""
    PROCESS_QUERY_INFORMATION = 0x0400
    TOKEN_QUERY = 0x0008
    TokenElevation = 20

    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32

    try:
        # 打开进程
        process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if not process:
            return None

        # 打开进程令牌
        token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(process, TOKEN_QUERY, ctypes.byref(token)):
            kernel32.CloseHandle(process)
            return None

        # 查询提升状态
        class TOKEN_ELEVATION(ctypes.Structure):
            _fields_ = [("TokenIsElevated", ctypes.c_ulong)]

        elevation = TOKEN_ELEVATION()
        size = ctypes.c_ulong()
        result = advapi32.GetTokenInformation(
            token, TokenElevation,
            ctypes.byref(elevation), ctypes.sizeof(elevation),
            ctypes.byref(size)
        )

        kernel32.CloseHandle(token)
        kernel32.CloseHandle(process)

        if result:
            return bool(elevation.TokenIsElevated)
        return None
    except:
        return None

def test_sendinput():
    """测试 SendInput 是否工作"""
    from input_manager import create_input_manager

    print("\n=== SendInput 测试 ===")
    print("3 秒后向当前窗口发送 'a' 键...")
    print("请切换到记事本或其他文本编辑器！\n")

    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    # 创建输入管理器
    im = create_input_manager(
        enable_diagnostics=True,
        backend="sendinput",
        target_hwnd=None,
        enable_focus_monitor=False
    )

    # 获取当前前台窗口
    hwnd, title, pid = get_foreground_window_info()
    print(f"\n发送目标: [{hwnd}] {title[:50]}...")

    # 检查目标进程权限
    target_elevated = check_process_elevation(pid)
    self_elevated = is_admin()

    print(f"目标进程权限: {'管理员' if target_elevated else '普通用户' if target_elevated is not None else '未知'}")
    print(f"本程序权限: {'管理员' if self_elevated else '普通用户'}")

    if target_elevated and not self_elevated:
        print("\n⚠️  警告: 目标以管理员运行，本程序以普通用户运行")
        print("   SendInput 可能被 UIPI 阻止！")

    # 发送按键
    print("\n发送 'a' 键...")
    success_press = im.press('a')
    time.sleep(0.05)
    success_release = im.release('a')

    # 获取诊断
    diag = im.get_diagnostics()
    stats = diag['stats']

    print(f"\n=== 诊断结果 ===")
    print(f"Backend: {diag['backend']}")
    print(f"Press API 调用: {'成功' if success_press else '失败'}")
    print(f"Release API 调用: {'成功' if success_release else '失败'}")
    print(f"统计 - Press: {stats['total_press']}, Failed: {stats['failed_press']}")

    print("\n如果记事本中没有出现 'a'，说明:")
    print("  1. 目标进程以管理员运行，需要以管理员身份运行本程序")
    print("  2. 或者目标进程有特殊的输入保护")

    im.stop()

def main():
    print("=" * 50)
    print("LyreAutoPlayer 输入诊断工具")
    print("=" * 50)

    # 1. 检查自身权限
    admin = is_admin()
    print(f"\n[1] 程序权限: {'✓ 管理员' if admin else '✗ 普通用户'}")
    if not admin:
        print("    建议: 右键 -> 以管理员身份运行")

    # 2. 检查当前前台窗口
    print("\n[2] 当前前台窗口:")
    hwnd, title, pid = get_foreground_window_info()
    print(f"    句柄: {hwnd}")
    print(f"    标题: {title[:60]}{'...' if len(title) > 60 else ''}")
    print(f"    PID: {pid}")

    target_elevated = check_process_elevation(pid)
    print(f"    权限: {'管理员' if target_elevated else '普通用户' if target_elevated is not None else '无法检测'}")

    # 3. UIPI 警告
    if target_elevated and not admin:
        print("\n" + "=" * 50)
        print("⚠️  UIPI 问题检测!")
        print("=" * 50)
        print("当前前台窗口以管理员权限运行，")
        print("但本程序以普通用户权限运行。")
        print("SendInput 发送的按键会被 Windows 静默丢弃！")
        print("\n解决方案:")
        print("  右键 main.py -> 以管理员身份运行")
        print("  或: 创建快捷方式 -> 属性 -> 兼容性 -> 以管理员身份运行")

    # 4. 可选测试
    print("\n" + "-" * 50)
    response = input("是否进行 SendInput 实际测试? (y/n): ").strip().lower()
    if response == 'y':
        test_sendinput()

    print("\n诊断完成。")

if __name__ == "__main__":
    main()
