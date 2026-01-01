# LyreAutoPlayer 制作指南

> 21/36 键自动演奏器 - 支持 MIDI 驱动、游戏兼容、预设系统

---

## 功能概览

- **21 键三行布局**: QWERTYU / ASDFGHJ / ZXCVBNM
- **36 键半音布局**: 支持全音阶游戏乐器
- **MIDI 驱动**: 直接读取 .mid 文件演奏
- **游戏兼容**: SendInput + 扫描码，支持 DirectX 游戏
- **10 种演奏风格**: 从机械精准到自由浪漫
- **6 个内置预设**: 一键切换常用配置
- **导入/导出**: JSON 格式设置分享

---

## 技术栈

| 组件 | 库 | 用途 |
|------|-----|------|
| GUI | PyQt6 | 图形界面 |
| MIDI 解析 | mido | 读取 .mid 文件 |
| 键盘模拟 | SendInput | 兼容 DirectX 游戏 |
| 窗口操作 | pywin32 | 选择目标窗口 |

---

## 安装与运行

```powershell
cd LyreAutoPlayer
python -m venv .venv
.\.venv\Scripts\activate
pip install PyQt6 mido keyboard pydirectinput
# 可选: pip install pyfluidsynth sounddevice pywin32
python main.py
```

---

## 键位布局

### 21 键模式（全音）

| 区域 | 键位 | 音符 |
|------|------|------|
| 高音区 | Q W E R T Y U | C5 D5 E5 F5 G5 A5 B5 |
| 中音区 | A S D F G H J | C4 D4 E4 F4 G4 A4 B4 |
| 低音区 | Z X C V B N M | C3 D3 E3 F3 G3 A3 B3 |

### 36 键模式（半音）

| 区域 | 白键 | 黑键 |
|------|------|------|
| 高音区 | Q W E R T Y U | 2 3 5 6 7 |
| 中音区 | Z X C V B N M | S D G H J |
| 低音区 | , . / I O P [ | L ; 9 0 - |

---

## 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| Middle-row Do | 中音区起始音高 | C4 (60) |
| Transpose | 整体升降调（半音） | 0 |
| Accidental Policy | 处理半音策略 | nearest |
| Speed | 播放速度倍率 | 1.0 |
| Press Duration | 按键时长 (ms) | 25 |
| Countdown | 倒计时切换窗口 | 2 秒 |

### 半音处理策略

| 策略 | 说明 |
|------|------|
| nearest | 就近选择最接近的可用音 |
| lower | 向下选择最近的可用音 |
| upper | 向上选择最近的可用音 |
| drop | 丢弃不可用的音 |

---

## 演奏风格 (10 种)

| 风格 | 描述 | 适用场景 |
|------|------|----------|
| mechanical | 精确机械 | 高速乐曲、需要精准触发 |
| natural | 自然流畅 | 日常演奏 |
| expressive | 富有感情 | 抒情曲目 |
| aggressive | 激进有力 | 节奏感强的曲目 |
| legato | 连贯延音 | 柔和的旋律 |
| staccato | 断奏短促 | 跳跃感的曲目 |
| swing | 爵士摇摆 | 爵士风格 |
| rubato | 自由速度 | 古典浪漫 |
| ballad | 慢速抒情 | 情歌 |
| lazy | 慵懒放松 | 轻松曲风 |

### 风格参数

| 参数 | 说明 |
|------|------|
| timing_offset_ms | 每个音符的随机时间偏移 |
| stagger_ms | 和弦分解时间（琶音效果） |
| duration_variation | 音符时值变化百分比 |

---

## 设置预设系统 (Session 3 新增)

### 6 个内置预设

| 预设 | 说明 | 参数特点 |
|------|------|----------|
| 快速精准 (fast_precise) | 最低延迟 | press_ms=15, 机械风格 |
| 自然流畅 (natural_flow) | 人性化 | press_ms=30, natural 风格 |
| 稳定兼容 (stable_compat) | 最大兼容性 | press_ms=50, 较长延迟 |
| 富有感情 (expressive_human) | 人性化+偶尔出错 | 启用错误模拟 |
| 21键默认 (21key_default) | 21键布局优化 | natural 风格 |
| 36键默认 (36key_default) | 36键布局优化 | natural 风格 |

### 预设 UI 操作

1. **选择预设**: Tab 1 顶部"设置预设"下拉框
2. **应用预设**: 点击"应用"按钮
3. **导入设置**: 点击"导入..."从 JSON 文件加载
4. **导出设置**: 点击"导出..."保存当前设置
5. **恢复默认**: 点击"恢复默认"重置所有设置

### 设置文件格式 (JSON)

```json
{
  "version": 3,
  "keyboard_preset": "21-key",
  "input_style": "natural",
  "press_ms": 25,
  "speed": 1.0,
  "use_midi_duration": true,
  "input_manager": {
    "backend": "sendinput",
    "min_press_interval_ms": 2.0,
    "min_hold_time_ms": 8.0
  },
  "error_config": {
    "enabled": false,
    "errors_per_8bars": 1
  }
}
```

---

## 输入系统 (Session 2 重写)

### SendInput + 扫描码后端

| 特性 | 说明 |
|------|------|
| 游戏兼容 | 使用硬件扫描码，DirectX 游戏可识别 |
| 长按支持 | KeyDown 保持到 KeyUp |
| 状态追踪 | RLock + 1:1 对应 |
| 异常保护 | 焦点丢失/退出时自动释放所有按键 |
| 诊断能力 | 详细统计（成功/失败次数） |

### 焦点监控

- 后台线程每 100ms 检查焦点
- 失焦时自动释放所有按键
- 防止按键卡住

---

## 全局热键

| 热键 | 功能 |
|------|------|
| F5 | 开始播放 |
| F6 | 停止播放 |
| F7 | 降低速度 |
| F8 | 提高速度 |
| F9 | 降低八度 |
| F10 | 提高八度 |
| F11 | 打开 MIDI |
| F12 | 切换时值模式 |

---

## 使用流程

1. **启动程序**: `python main.py`
2. **加载 MIDI**: 点击 "Load MIDI" 选择文件
3. **选择预设**: 从"设置预设"下拉框选择合适的预设
4. **选择窗口**: 下拉框选择目标游戏窗口
5. **开始播放**: 点击 "Start" 或按 F5
6. **切换窗口**: 倒计时期间切换到游戏
7. **停止播放**: 点击 "Stop" 或按 F6

---

## 故障排查

### 游戏内按键不触发

1. 以管理员身份运行程序
2. 检查诊断输出: `[Input] Backend: SendInput (scancode)`
3. 尝试"稳定兼容"预设

### 按键卡住

- 程序有多重保护机制
- 手动按一下卡住的键释放
- 或重启程序

### 音符丢失

1. 降低速度 (Speed < 1.0)
2. 增加 press_ms
3. 使用"稳定兼容"预设

---

## 验收命令

```powershell
cd D:\dw11\piano\LyreAutoPlayer

# 1. 回归测试
.venv\Scripts\python.exe test_regression.py
# 预期: 16/16 PASS

# 2. 输入系统测试
.venv\Scripts\python.exe test_input_manager.py --quick
# 预期: All basic tests passed

# 3. 运行主程序
.venv\Scripts\python.exe main.py
# 验证 Tab 1 显示"设置预设"组
```

---

## 文件结构

```
LyreAutoPlayer/
├── main.py              # 主程序、UI、播放逻辑
├── input_manager.py     # 输入系统 (SendInput 后端)
├── keyboard_layout.py   # 键位布局定义
├── settings_manager.py  # 设置管理、预设、验证
├── test_regression.py   # 回归测试
├── test_input_manager.py # 输入系统测试
├── requirements.txt     # 依赖列表
└── .venv/               # 虚拟环境
```

---

## 开发历史

| Session | 日期 | 改动 |
|---------|------|------|
| 1 | 2026-01-01 | 初始化项目骨架 |
| 2 | 2026-01-01 | 重写 input_manager.py (SendInput + 扫描码) |
| 3 | 2026-01-01 | 创建 settings_manager.py、test_regression.py |
| 4 | 2026-01-01 | 集成 settings_manager 到 UI (预设/导入/导出) |

---

## 乐谱来源

这版直接吃 **MIDI**。如果你只有五线谱/简谱：
- 用 MuseScore 等工具导出 `.mid`
- 或使用 EOP (EveryonePiano) 转 MIDI 工具: `analyzetools/eop/eop_to_midi_final.py`

---

*最后更新: 2026-01-01 Session 4*
