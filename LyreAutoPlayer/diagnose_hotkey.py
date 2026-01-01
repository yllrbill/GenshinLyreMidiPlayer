#!/usr/bin/env python3
"""
诊断全局热键问题
运行方式: 以管理员身份运行此脚本，然后切换到游戏窗口按 F5
"""
import sys
import ctypes
import time

def is_admin():
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

print("=" * 50)
print("全局热键诊断工具")
print("=" * 50)

# 1. 检查管理员权限
admin = is_admin()
print(f"\n[1] 管理员权限: {'✓ 是' if admin else '✗ 否 (这是问题根源!)'}")
if not admin:
    print("    → keyboard 库需要管理员权限才能捕获游戏窗口的按键")
    print("    → 解决方案: 右键 → 以管理员身份运行")

# 2. 检查 keyboard 库
print("\n[2] keyboard 库导入测试...")
try:
    import keyboard as kb
    print("    ✓ keyboard 库导入成功")
except ImportError as e:
    print(f"    ✗ keyboard 库未安装: {e}")
    print("    → pip install keyboard")
    sys.exit(1)

# 3. 测试热键注册
print("\n[3] 热键注册测试...")
test_results = {"f5": False, "f6": False}

def on_f5():
    test_results["f5"] = True
    print("\n    ★★★ F5 按键捕获成功! ★★★")

def on_f6():
    test_results["f6"] = True
    print("\n    ★★★ F6 按键捕获成功! ★★★")

try:
    kb.add_hotkey('f5', on_f5, suppress=False)
    kb.add_hotkey('f6', on_f6, suppress=False)
    print("    ✓ 热键注册成功 (F5, F6)")
except Exception as e:
    print(f"    ✗ 热键注册失败: {e}")
    sys.exit(1)

# 4. 等待用户测试
print("\n" + "=" * 50)
print("测试说明:")
print("  1. 保持此窗口打开")
print("  2. 切换到游戏窗口 (Alt+Tab)")
print("  3. 在游戏中按 F5 或 F6")
print("  4. 观察此窗口是否显示'捕获成功'")
print("=" * 50)
print("\n等待按键... (按 Ctrl+C 退出)")

try:
    # 持续运行等待按键
    while True:
        time.sleep(0.1)
        if test_results["f5"] or test_results["f6"]:
            print("\n[结论] 全局热键工作正常!")
            print("       如果在游戏中测试，说明热键配置正确。")
            break
except KeyboardInterrupt:
    print("\n\n已退出")
finally:
    kb.unhook_all_hotkeys()

if not test_results["f5"] and not test_results["f6"]:
    print("\n[结论] 未检测到按键")
    if not admin:
        print("       最可能原因: 未以管理员身份运行")
    else:
        print("       可能原因:")
        print("       - 游戏使用 DirectInput 阻止了全局 hook")
        print("       - 需要使用 RegisterHotKey API 替代")
