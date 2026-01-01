# Handoff Format

analydocs/HANDOFF.md 必须包含以下章节：

## Goals
本次目标与范围

## Verified Facts
每条带命令/路径/哈希的已验证事实

## Blockers
当前阻塞点（缺输入/权限/环境）

## Next Steps
下一步最短路径（≤7步 + 命令）

## Acceptance Status
验收清单状态：
- PASS: 已通过验证
- FAIL: 验证失败
- UNKNOWN: 未验证

## Files Touched
按排序列出本次读过/改过/新增的文件

---

## 示例

```markdown
# Handoff - 2025-12-25

## Goals
解密 neox.xml，建立可复用流程

## Verified Facts
- neox.xml SHA256: `c1474102fa...` (3456 bytes)
  ```powershell
  python -c "import hashlib; print(hashlib.sha256(open('neox.xml','rb').read()).hexdigest())"
  ```
- neox_engine.dll SHA256: `e56e81fa...`

## Blockers
- set_ccz_decrypt_key 从未被调用（需寻找替代入口）

## Next Steps
1. Hook CryptoAPI (CryptDecrypt)
2. 搜索 AES S-Box 常量
3. ...

## Acceptance Status
- [ ] UNKNOWN: 解密成功

## Files Touched
- analydocs/HANDOFF.md (更新)
- analyzetools/read_key_from_memory.py (读取)
```
