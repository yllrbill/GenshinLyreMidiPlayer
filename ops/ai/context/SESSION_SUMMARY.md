- 背景/目标:
  处理用户新增需求与回归问题（小节选择/拉伸、拖拽黄线、时间轴行高调整、滚动同步），并对现有改动进行 message-review 审计与纠偏建议。
- 已完成:
  基于用户提供的变更审计报告与代码核查，定位关键风险并给出修复提示词；更新 session-summary 记录。
- 关键修改:
  无新的代码修改；本次仅审计并提出修正建议。
- 相关文件:
  - LyreAutoPlayer/ui/editor/piano_roll.py：发现小节编号 1-based 与现有公式不一致、非连续小节拉伸逻辑不正确、增量应按小节数累计、音符命中判定建议用区间重叠。
  - LyreAutoPlayer/ui/editor/timeline.py：Ctrl 拖拽仍绘制蓝色选区；小节选择/拖拽信号已新增但需按需求调整。
  - LyreAutoPlayer/ui/editor/editor_window.py：未选中小节提示为英文硬编码，建议改为 tr()；需监听 sig_notes_changed 统一刷新 key_list/timeline（先前建议）。
  - LyreAutoPlayer/i18n/translations.py：建议补充小节相关提示的中文键值。
  - LyreAutoPlayer/ui/editor/undo_commands.py：新增 AdjustBarsDurationCommand 已存在（依赖 weakref 已补）。
- 验证:
  未运行测试；用户提供了运行时错误与截图作为证据。
- 风险/待办:
  1) 修复小节编号 off-by-one，避免选中/拉伸错位；2) 支持 Ctrl 多选非连续小节分段拉伸；3) 增量按小节数累计；4) Ctrl 拖拽仅显示黄线，去掉蓝色选区；5) 提示文案 i18n。
- 下一步:
  让 Claude 按提示词实施修复，并回归验证：Ctrl+拖拽多选、单击精确跳转、黄线显示、选中小节反色、按小节拉伸/压缩与滚动同步。
