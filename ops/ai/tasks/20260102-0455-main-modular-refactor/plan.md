# Plan: Main.py Modular Refactor

## Goal/Scope

将 `LyreAutoPlayer/main.py` 精简为核心功能入口，其他功能拆分为扩展模块或插件（含语言/i18n），确保重构后所有功能完整且无行为回归。

## Constraints/Assumptions

- `ops/ai/tasks/20260102-0251-main-modular-refactor/evidence/context_pack.md` 缺失，本计划基于 `request.md` 与现有仓库结构推断。
- 当前 `LyreAutoPlayer/main.py` 约 3825 行，作为重构缩减的基线参考。
- 功能不丢失：播放、量化、输入、错误模拟、8-bar、UI 配置、快捷键、浮窗、i18n 等均需保留
- 重构后仍应可直接运行 `LyreAutoPlayer/main.py`（或等效入口），不增加用户启动复杂度
- 插件加载失败需可降级并提示，不应导致主程序崩溃
- 启动脚本（如 `LyreAutoPlayer/RunAsAdmin.bat`）与入口路径保持可用
- 分阶段推进，每一步都可运行与回滚，避免一次性大改造成不可用

## Plan Steps

### Phase 1: 分析与设计

1. **盘点 main.py 功能模块与耦合点**
   - 影响文件: `LyreAutoPlayer/main.py`
   - 输出: 模块边界清单（UI 构建、播放线程、MIDI 解析、输入管理、错误模拟、8-bar、i18n、浮窗、快捷键等）
   - 验收: 产出 `evidence/module_inventory.md`
   - 补充: 标记可能重复的功能/流程（相似 UI 构建、重复的参数处理、重复的时间/节拍计算等）

2. **重复功能排查与合并策略**
   - 目标: 识别并合并重复逻辑，减少代码体积与维护成本
   - 方法: 统计同名/同义功能块、抽取公共工具函数、统一配置与计算流程
   - 输出: `evidence/dedup_plan.md`（列出重复点、合并方案与风险）
   - 判定规则: 同类 UI 构建流程重复 ≥2 处、相似参数校验/默认值处理重复 ≥2 处、时间/节拍/速度计算重复 ≥2 处、i18n 文案绑定重复 ≥2 处、日志/提示语拼接重复 ≥2 处
   - 合并策略: 提炼公共函数或基类；对 UI 采用“配置驱动生成”或统一 builder；对计算逻辑建 `utils` 或 `core` 服务；避免改动行为的“纯重构”
   - 可进一步抽象项（优先级高）:
     - UI 控件构建与布局：统一 SpinBox/ComboBox/Label/Row 的创建与默认值设置
     - 配置读写与校验：默认值、边界检查、序列化/反序列化集中
     - 计时/节拍/速度计算：beat/bar/tempo 相关函数收敛为 `utils.timing`
     - i18n 绑定：批量设置 label/text/tooltip 的统一入口
     - 日志输出格式：统一前缀/级别/格式化，减少散落的 `append_log`
     - UI 同步逻辑：Tab 之间的同步（如错误/8-bar 快捷项）抽成独立同步器

3. **定义核心与插件边界**
   - 核心保留: 程序入口、配置模型、事件调度、插件加载与生命周期管理
   - 插件范围: UI 面板、播放逻辑、输入管理、i18n、错误模拟、8-bar
   - 验收: 产出 `evidence/architecture_design.md`

4. **设计插件接口（最小 API）**
   - 接口定义: `register(app)`, `on_load()`, `on_unload()`
   - 核心服务: 日志、配置、事件总线、UI 钩子
   - 插件发现/启停/加载顺序: 目录扫描或清单配置，默认全启用，允许单独禁用
   - 验收: 产出 `evidence/plugin_interface.md`

### Phase 2: 核心模块拆分

5. **拆分 i18n 模块**
   - 影响文件: `LyreAutoPlayer/main.py` → `LyreAutoPlayer/i18n/`
   - 内容: 翻译字典、语言切换逻辑、`tr()` 函数
   - 验收: `python -m py_compile LyreAutoPlayer/i18n/__init__.py` 通过

6. **拆分配置管理模块**
   - 影响文件: `LyreAutoPlayer/main.py` → `LyreAutoPlayer/core/config.py`
   - 内容: 配置读写、默认值、迁移兼容
   - 验收: 旧配置文件可正常加载

7. **拆分事件总线**
   - 影响文件: 新建 `LyreAutoPlayer/core/events.py`
   - 内容: 事件发布/订阅机制，解耦模块间通信
   - 验收: 最小自检（导入/发布/订阅示例）可运行

### Phase 3: 功能模块拆分

8. **拆分播放与输入模块**
   - 影响文件: `LyreAutoPlayer/main.py` → `LyreAutoPlayer/player/`
   - 内容: PlayerThread、MIDI 解析、输入管理、IME 控制
   - 验收: MIDI 播放功能正常

9. **拆分错误模拟模块**
   - 影响文件: `LyreAutoPlayer/main.py` → `LyreAutoPlayer/plugins/errors.py`
   - 内容: 错误生成逻辑、错误类型配置
   - 验收: 错误模拟功能正常

10. **拆分 8-bar 模块**
   - 影响文件: `LyreAutoPlayer/main.py` → `LyreAutoPlayer/plugins/eight_bar.py`
   - 内容: 8-bar 模式、节拍锁定、时值变化
   - 验收: 8-bar 功能正常

### Phase 4: UI 模块拆分

11. **拆分 UI 面板**
    - 影响文件: `LyreAutoPlayer/main.py` → `LyreAutoPlayer/ui/`
    - 内容: 各 Tab 面板、浮窗、快捷键设置
    - 验收: UI 布局与功能不变

12. **重构主窗体**
    - 影响文件: `LyreAutoPlayer/main.py`
    - 内容: 只保留容器与布局注册，调用各 UI 模块
    - 验收: 主窗口正常显示

### Phase 5: 集成与验证

13. **实现插件加载器**
    - 影响文件: `LyreAutoPlayer/core/plugin_loader.py`
    - 内容: 插件发现、启停配置、加载顺序、生命周期管理、错误降级
    - 验收: 插件加载/卸载正常

14. **回归验证**
    - 验证项: 播放、快捷键、浮窗、语言切换、错误模拟、8-bar、诊断
    - 验收: 所有功能行为与重构前一致
    - 补充: 每个阶段完成后至少执行一次基础可运行性验证

15. **清理与文档**
    - 更新 README 或使用说明
    - 标注插件目录结构与扩展方式

## 可进一步分离清单（基于 main-summary）

> 以下为后续可选优化项，按推荐执行顺序排列。
> 每项列出对应方法名、目标文件路径、行数估算。

### 推荐拆分顺序

```
1. 通用工具与常量 (无依赖，基础层)
2. 设置持久化 (配置读写，被多模块依赖)
3. 全局热键 (独立功能)
4. 播放控制 (核心逻辑)
5. UI Tab 拆分 (体积最大)
6. 语言/翻译绑定 (依赖 UI)
7. 预设与风格 (依赖 UI + 配置)
8. 配置收集与应用 (依赖 UI + 预设)
9. 错误与 8-bar 同步器 (依赖 UI)
10. 键盘显示/窗口/日志 (UI 组件)
11. 文件/音色操作 (UI 对话框)
12. 测试/调试入口 (最低优先级)
```

---

### 1. 通用工具与常量 [优先级: P0]

**目标路径:**
- `LyreAutoPlayer/core/utils.py`
- `LyreAutoPlayer/core/constants.py`

**方法清单 (L76-186):**
| 方法/常量 | 行号 | 说明 |
|-----------|------|------|
| `is_admin()` | L76-84 | 检查管理员权限 |
| `get_best_audio_driver()` | L86-95 | 选择音频驱动 |
| `list_windows()` | L97-113 | 枚举可见窗口 |
| `load_settings_from_file()` | L115-126 | JSON 加载 |
| `get_saved_theme()` | L128-143 | 获取主题设置 |
| `SETTINGS_FILE`, `SETTINGS_VERSION`, `SETTINGS_*_DIR` | L144-155 | 设置常量 |
| `DEFAULT_TEMPO_US`, `DEFAULT_BPM`, `DEFAULT_BEAT_DURATION`, `DEFAULT_BAR_DURATION`, `DEFAULT_SEGMENT_BARS` | L157-162 | 时间常量 |
| `PRESET_COMBO_ITEMS`, `DEFAULT_KEYBOARD_PRESET` | L173-178 | 预设常量 |
| `GM_PROGRAM` | L155 | MIDI 音色号 |

**预计行数:** ~120 行

---

### 2. 设置持久化 [优先级: P0]

**目标路径:** `LyreAutoPlayer/core/settings_store.py`

**方法清单 (L1910-2134):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `save_settings()` | L1910-1969 | 保存设置到 JSON (~60 行) |
| `load_settings()` | L1971-2133 | 加载设置 + 自定义风格 (~160 行) |

**预计行数:** ~220 行

---

### 3. 全局热键 [优先级: P1]

**目标路径:** `LyreAutoPlayer/core/hotkeys.py`

**方法清单 (L1880-1908):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `_register_global_hotkeys()` | L1880-1908 | 注册 F5-F12 全局热键 |

**热键映射:**
- F5: `on_toggle_play_pause`
- F6: `on_stop`
- F7: `on_speed_down`
- F8: `on_speed_up`
- F9: `on_octave_down`
- F10: `on_octave_up`
- F11: `on_load`
- F12: `on_toggle_midi_duration`

**预计行数:** ~50 行

---

### 4. 播放控制 [优先级: P1]

**目标路径:** `LyreAutoPlayer/core/playback_controller.py`

**方法清单 (L1713-1878):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `collect_cfg()` | L1713-1746 | 收集 PlayerConfig (~35 行) |
| `on_start()` | L1748-1767 | 开始播放 (~20 行) |
| `on_toggle_play_pause()` | L1769-1797 | 切换播放/暂停 (~30 行) |
| `on_stop()` | L1799-1805 | 停止播放 (~7 行) |
| `on_pause()` | L1807-1817 | 暂停/恢复 (~11 行) |
| `on_finished()` | L1819-1824 | 播放完成回调 (~6 行) |
| `_on_thread_paused()` | L1826-1829 | 线程暂停回调 (~4 行) |
| `on_octave_up()` | L1831-1836 | 八度 +1 (~6 行) |
| `on_octave_down()` | L1838-1843 | 八度 -1 (~6 行) |
| `on_toggle_midi_duration()` | L1845-1849 | 切换时长模式 (~5 行) |
| `on_speed_up()` | L1851-1856 | 速度 +0.1 (~6 行) |
| `on_speed_down()` | L1858-1863 | 速度 -0.1 (~6 行) |
| `on_show_floating()` | L1865-1878 | 显示浮动控制器 (~14 行) |

**预计行数:** ~170 行

---

### 5. UI Tab 拆分 [优先级: P2] ⭐ 体积最大

**目标路径:**
- `LyreAutoPlayer/ui/tabs/__init__.py`
- `LyreAutoPlayer/ui/tabs/main_tab.py`
- `LyreAutoPlayer/ui/tabs/keyboard_tab.py`
- `LyreAutoPlayer/ui/tabs/shortcuts_tab.py`
- `LyreAutoPlayer/ui/tabs/input_style_tab.py`
- `LyreAutoPlayer/ui/tabs/errors_tab.py`

**方法清单 (L211-826，共 615 行):**
| Tab | 行范围 | 目标文件 | 说明 |
|-----|--------|----------|------|
| `init_ui()` 框架 | L211-259 | 保留 main.py | TabWidget 容器 (~50 行) |
| Tab 1 Main | L260-590 | `main_tab.py` | 文件/配置/音效/快捷错误/8bar/预设 (~330 行) |
| Tab 2 Keyboard | L592-620 | `keyboard_tab.py` | 键位映射显示 (~30 行) |
| Tab 3 Shortcuts | L622-670 | `shortcuts_tab.py` | 热键显示 (~50 行) |
| Tab 4 Input Style | L672-730 | `input_style_tab.py` | 风格参数/8bar 设置 (~60 行) |
| Tab 5 Errors | L732-799 | `errors_tab.py` | 错误模拟设置 (~70 行) |

**预计行数:** ~540 行 (从 main.py 移出)

---

### 6. 语言/翻译绑定 [优先级: P2]

**目标路径:** `LyreAutoPlayer/ui/i18n_binder.py`

**方法清单 (L827-946):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `apply_language()` | L827-937 | 应用翻译到所有 UI 元素 (~110 行) |
| `on_language_changed()` | L939-945 | 语言切换回调 (~7 行) |

**预计行数:** ~120 行

---

### 7. 预设与风格 [优先级: P2]

**目标路径:** `LyreAutoPlayer/core/presets.py`

**方法清单 (L947-1252):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `on_preset_changed()` | L947-953 | 主选项卡键盘预设变化 (~7 行) |
| `on_kb_preset_changed()` | L955-961 | 键盘选项卡预设变化 (~7 行) |
| `_rebuild_style_combo()` | L965-980 | 重建风格下拉 (~16 行) |
| `_rebuild_all_style_combos()` | L982-996 | 重建所有风格下拉 (~15 行) |
| `_rebuild_settings_preset_combo()` | L998-1007 | 重建设置预设下拉 (~10 行) |
| `_select_style_in_combo()` | L1009-1016 | 选择风格 (~8 行) |
| `_update_style_params_display()` | L1018-1036 | 更新风格参数显示 (~19 行) |
| `on_input_style_changed()` | L1038-1060 | 主设置风格变化 (~23 行) |
| `on_style_tab_changed()` | L1062-1084 | 风格选项卡变化 (~23 行) |
| `on_add_custom_style()` | L1086-1126 | 添加自定义风格 (~41 行) |
| `on_delete_custom_style()` | L1128-1159 | 删除自定义风格 (~32 行) |
| `on_apply_style_params()` | L1161-1194 | 应用风格参数 (~34 行) |
| `on_apply_settings_preset()` | L1198-1252 | 应用内置预设 (~55 行) |

**预计行数:** ~290 行

---

### 8. 配置收集与应用 [优先级: P2]

**目标路径:** `LyreAutoPlayer/core/config_ui.py`

**方法清单 (L1254-1447):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `on_import_settings()` | L1254-1274 | 导入 JSON 设置 (~21 行) |
| `on_export_settings()` | L1276-1298 | 导出 JSON 设置 (~23 行) |
| `on_reset_defaults()` | L1300-1335 | 重置默认设置 (~36 行) |
| `_collect_current_settings()` | L1337-1365 | 收集当前 UI 设置 (~29 行) |
| `_apply_settings_dict()` | L1367-1447 | 应用设置字典到 UI (~81 行) |

**预计行数:** ~190 行

---

### 9. 错误与 8-bar 同步器 [优先级: P3]

**目标路径:**
- `LyreAutoPlayer/ui/syncers/__init__.py`
- `LyreAutoPlayer/ui/syncers/error_syncer.py`
- `LyreAutoPlayer/ui/syncers/eight_bar_syncer.py`

**错误同步方法 (L1582-1648):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `_on_error_enabled_changed()` | L1582-1587 | 错误启用变化 (~6 行) |
| `_on_error_freq_changed()` | L1589-1593 | 错误频率变化 (~5 行) |
| `_on_quick_error_enable_changed()` | L1595-1604 | 快捷错误开关 (~10 行) |
| `_sync_quick_errors_to_tab5()` | L1606-1622 | 快捷→Tab5 同步 (~17 行) |
| `_sync_tab5_errors_to_quick()` | L1624-1630 | Tab5→快捷同步 (~7 行) |
| `_sync_tab5_to_quick_errors()` | L1632-1648 | 反向同步 (~17 行) |

**8-bar 同步方法 (L1650-1712):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `_on_eight_bar_enabled_changed()` | L1652-1662 | 8bar 启用变化 (~11 行) |
| `_apply_eight_bar_preset()` | L1664-1678 | 应用 8bar 预设 (~15 行) |
| `_collect_eight_bar_style()` | L1680-1695 | 收集 EightBarStyle (~16 行) |
| `_on_quick_eight_bar_changed()` | L1697-1705 | 快捷 8bar 同步 (~9 行) |
| `_sync_eight_bar_to_quick()` | L1707-1711 | 8bar→快捷同步 (~5 行) |

**预计行数:** ~120 行

---

### 10. 键盘显示/窗口/日志 [优先级: P3]

**目标路径:**
- `LyreAutoPlayer/ui/widgets.py`
- `LyreAutoPlayer/core/window_manager.py`

**方法清单 (L1449-1539):**
| 方法 | 行号 | 目标文件 | 说明 |
|------|------|----------|------|
| `_build_keyboard_display()` | L1449-1506 | `ui/widgets.py` | 构建键盘网格 (~58 行) |
| `show_init_messages()` | L1508-1527 | `ui/widgets.py` | 初始化消息 (~20 行) |
| `append_log()` | L1529-1530 | `ui/widgets.py` | 追加日志 (~2 行) |
| `refresh_windows()` | L1532-1539 | `core/window_manager.py` | 刷新窗口列表 (~8 行) |

**预计行数:** ~90 行

---

### 11. 文件/音色操作 [优先级: P3]

**目标路径:** `LyreAutoPlayer/core/file_dialogs.py`

**方法清单 (L1541-1580):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `on_load()` | L1541-1566 | 加载 MIDI 文件 (~26 行) |
| `on_browse_sf()` | L1568-1580 | 浏览 SoundFont (~13 行) |

**预计行数:** ~40 行

---

### 12. 测试/调试入口 [优先级: P4]

**目标路径:** `LyreAutoPlayer/tools/debug.py`

**方法清单 (L2164-2260):**
| 方法 | 行号 | 说明 |
|------|------|------|
| `on_test()` | L2164-2168 | 测试按键 (~5 行) |
| `on_test_sound()` | L2170-2260 | 测试 FluidSynth (~90 行) |

**预计行数:** ~100 行

---

### 拆分后预期效果

| 模块 | 预计行数 | main.py 减少 |
|------|----------|--------------|
| core/utils.py + constants.py | ~120 | -120 |
| core/settings_store.py | ~220 | -220 |
| core/hotkeys.py | ~50 | -50 |
| core/playback_controller.py | ~170 | -170 |
| ui/tabs/* | ~540 | -540 |
| ui/i18n_binder.py | ~120 | -120 |
| core/presets.py | ~290 | -290 |
| core/config_ui.py | ~190 | -190 |
| ui/syncers/* | ~120 | -120 |
| ui/widgets.py + window_manager.py | ~90 | -90 |
| core/file_dialogs.py | ~40 | -40 |
| tools/debug.py | ~100 | -100 |
| **总计** | **~2050** | **-2050** |

**预计 main.py 最终行数:** 1961 - 2050 ≈ **~100 行** (仅保留入口 + Tab 容器框架)

## Acceptance Checklist

- [ ] `main.py` 只保留核心入口与插件加载逻辑，体积显著缩小
- [ ] i18n 独立为模块/插件，语言切换与 `tr()` 功能正常
- [ ] UI 各 tab/面板已拆分为模块或插件，功能与布局不变
- [ ] 播放、输入、错误模拟、8-bar 等功能按模块拆分后可正常工作
- [ ] 配置兼容性保持，旧配置无需迁移即可运行
- [ ] 插件加载失败可降级并提示，主程序稳定运行
- [ ] 手动验证覆盖主要功能入口与关键操作
- [ ] `python -m py_compile LyreAutoPlayer/main.py` 与关键模块无语法错误
- [ ] `LyreAutoPlayer/RunAsAdmin.bat` 仍能正常启动主程序
- [ ] 分阶段产物可运行且可回滚，未出现“不可启动”的中间状态

## Risks/Dependencies

- 拆分过程中跨模块引用较多，需避免循环依赖
- 插件接口设计不当可能导致后续扩展困难或破坏现有调用路径

---
*Created: 2026-01-02 02:51*
