# Windows Shell Discipline (Hard Rules)

> Project-level copy. Inherits from user-level `~/.claude/rules/windows-shell.md`.
> Override specific rules here if project needs differ.

## HR0: Default Shell
- Default to PowerShell for any multi-step logic on Windows.
- Bash is allowed only for simple read-only utilities (rg/ls/cat/sed) and single-step commands.

## HR1: Never inline complex PowerShell inside Bash
- FORBIDDEN: `powershell -Command " ... $var ... $_ ... "`
Reason: Bash expands `$var` and `$_` before PowerShell receives it; `$_` is a Bash special parameter (last arg of previous command), and will corrupt PowerShell pipeline variables. (This causes real parse errors.)

## HR2: Always write a .ps1 file, then run powershell -File
- Any loop / pipeline / multi-line logic MUST be written to a `.ps1` file via Claude's file tools (Write/Edit).
- Then execute:
  `powershell -NoProfile -ExecutionPolicy Bypass -File <path.ps1>`

## HR3: Use Claude file tools to avoid quoting bugs
- Prefer: Write/Edit a script file (ps1) with Claude tool.
- Avoid: heredoc/cat/complex quoting in Bash.

## HR4: PowerShell quoting rules
- Use single quotes for literals. Use double quotes only when intentional interpolation is needed.

## HR5: Determinism + Logs
- All lists must be explicitly sorted.
- Every test/run writes logs to `.claude/state/...` for replay.

## HR6: Smoke test template rule
- For smoke tests: create `.claude/state/thinking/_smoke/<SMOKE_ID>/`
- SMOKE_ID must be UTC ISO-like `yyyyMMddTHHmmssZ`
- Validate artifacts by existence + envelope-first in artifact files

---

*Created: 2025-12-28*
*Scope: Project-level (d:\dw11)*
*Parent: ~/.claude/rules/windows-shell.md*
