# -*- coding: utf-8 -*-
"""Fix all multi-line translation strings in main.py"""

import re

# Multi-line translations that need fixing
MULTILINE_FIXES = {
    "admin_ok": "[OK] Admin: True - 以管理员身份运行（可向所有窗口发送输入）",
    "admin_warn": "[WARN] Admin: False - 如果游戏以管理员身份运行，输入将被 Windows UIPI 阻止",
    "uipi_hint": "[INFO] UIPI（用户界面特权隔离）：Windows 阻止非管理员程序向管理员程序发送输入。如果按键不生效，请以管理员身份运行本工具。",
    "ready_msg": "就绪。先选窗口，然后点 Start；倒计时期间切回游戏即可。",
    "sound_hint": "提示：启用本地音效需要 SoundFont (.sf2) 文件。",
}

def fix_main_py():
    with open('main.py', 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    for key, correct_zh in MULTILINE_FIXES.items():
        # Find the key's dict block and replace LANG_ZH value
        # Pattern: "key": {\n        LANG_EN: "...",\n        LANG_ZH: "...",\n    },
        # or: "key": {\n        LANG_EN: "..." "...",\n        LANG_ZH: "..." "...",\n    },

        # Use a more flexible pattern
        pattern = rf'("{key}": \{{\s*LANG_EN: [^,]+,\s*LANG_ZH: ")[^"]*(?:"[^"]*)*("[,\s]*\}})'

        # Count matches
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            # Replace
            def replacer(m):
                return m.group(1) + correct_zh + '",\n    }'
            content = re.sub(pattern, replacer, content, flags=re.DOTALL)
            print(f"Fixed {key}")
        else:
            print(f"Pattern not found for {key}, trying alternative...")
            # Alternative: find the line and replace everything after LANG_ZH:
            lines = content.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if f'"{key}":' in line and '{' in line:
                    # Found the key, collect lines until closing }
                    block_lines = [line]
                    i += 1
                    while i < len(lines) and '    },' not in lines[i] and '    }' not in lines[i]:
                        block_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        block_lines.append(lines[i])

                    # Rebuild the block with correct LANG_ZH
                    # Find LANG_EN part
                    block = '\n'.join(block_lines)
                    en_match = re.search(r'LANG_EN: ("[^"]*"(?:\s*"[^"]*")*)', block)
                    if en_match:
                        en_value = en_match.group(1)
                        new_block = f'    "{key}": {{\n        LANG_EN: {en_value},\n        LANG_ZH: "{correct_zh}",\n    }},'
                        new_lines.append(new_block)
                        print(f"Fixed {key} (alternative)")
                    else:
                        new_lines.extend(block_lines)
                else:
                    new_lines.append(line)
                i += 1
            content = '\n'.join(new_lines)

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Done")

if __name__ == '__main__':
    fix_main_py()
