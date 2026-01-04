# /repo-push - 安全自动提交流程

在当前仓库根目录执行"安全自动提交流程"。

## 功能

1. **证据收集** - 输出 pwd、repo root、git status
2. **无变更检查** - 若无变更则退出
3. **同步远端** - `git pull --rebase --autostash`
4. **敏感文件检查** - 阻止 .env、*key*、*token* 等文件提交
5. **提交** - `git add -A && git commit -m "autosave: YYYY-MM-DD HH:MM:SS"`
6. **推送** - `git push -u origin HEAD`
7. **主分支合并** - 若不在主分支，切换并合并（优先 ff）

## 安全保证

- 发现冲突立即停止，不自动解决
- 检测到敏感文件立即停止
- 禁止 force push
- 禁止修改历史

## 使用

```
/repo-push
```

## 执行

调用 skill `repo-push-core` 执行完整流程。
