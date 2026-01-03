- 背景/目标:
  - 活跃任务: 20260103-midi-editor-pipeline（MIDI 钢琴卷帘编辑器），Phase 1/1.5 已完成，准备进入 Phase 2（完整体验基础编辑）。
  - 需求确认: 版本选择取消默认加载最新保存版本；主界面 mid_path 显示选中版本；保存目录改为 LyreAutoPlayer\midi-change。

- 已完成:
  - EditorWindow/PianoRoll/Timeline/Keyboard/NoteItem 基础骨架可运行，支持加载 MIDI、显示音符、播放头、缩放、保存索引。
  - Phase 1 修复：坐标基准统一 NOTE_RANGE、renderHint 修复、tempo map 处理、重叠音符处理、选择状态联动。
  - Phase 1.5 集成：main.py 选择版本后统一加载（主界面+编辑器）；版本选择弹窗；i18n 文案新增。
  - 版本管理优化：保存目录改为 midi-change；按 last_modified 逆序；取消选择默认最新；过滤失效版本；编辑器 Ctrl+O 与主界面逻辑一致；i18n 文案统一且语言跟随父窗口。
  - 诊断窗口修复（追加到 20260102-2138）：信号线程安全、语言同步、KeySource 防御、按钮可见性无条件同步。
  - 新增 skill: message-review；规则已补充“给 Claude 提示词使用本机路径 d:\dw11\piano”。

- 关键修改:
  - 保存版本目录从 midi/edited → midi-change；索引使用 index.json。
  - 主界面 on_load() 改为先选版本再加载 events，并用同一路径打开编辑器。
  - 编辑器版本选择逻辑默认最新、取消也加载最新、i18n 跟随父窗口语言。

- 相关文件:
  - LyreAutoPlayer/ui/editor/editor_window.py
  - LyreAutoPlayer/ui/editor/piano_roll.py
  - LyreAutoPlayer/ui/editor/note_item.py
  - LyreAutoPlayer/ui/editor/keyboard.py
  - LyreAutoPlayer/main.py
  - LyreAutoPlayer/ui/__init__.py
  - LyreAutoPlayer/i18n/translations.py
  - LyreAutoPlayer/ui/mixins/config_mixin.py
  - LyreAutoPlayer/ui/mixins/settings_preset_mixin.py
  - /home/yllrb/.codex/skills/message-review/SKILL.md

- 验证:
  - .venv\Scripts\python.exe -m py_compile ui/editor/*.py / main.py 等通过
  - from ui import EditorWindow / from main import MainWindow 通过

- 风险/待办:
  - Phase 2 未开始：完整体验编辑（选择/移动/删除/复制粘贴、框选、多选、网格吸附、右键删除、粘贴位置）。
  - 编辑器保存仍为“直接保存原始 MIDI”（Phase 2 才重建 MIDI）。

- 下一步:
  - 执行 20260103-midi-editor-pipeline Phase 2（完整体验版）实现基础编辑交互。
