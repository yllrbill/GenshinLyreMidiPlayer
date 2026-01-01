"""
Settings Manager - 统一配置管理模块

功能：
1. Schema 定义与校验
2. 预设系统（内置 + 自定义）
3. 版本迁移
4. 导入/导出
5. 默认值管理

Author: LyreAutoPlayer v3
"""

import json
import os
import copy
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# ============== 版本常量 ==============
SETTINGS_VERSION = 3  # 当前设置版本，用于迁移

# ============== Schema 定义 ==============

@dataclass
class InputStyleParams:
    """输入风格参数"""
    timing_offset_min_ms: int = 0
    timing_offset_max_ms: int = 0
    stagger_ms: int = 0
    duration_variation: float = 0.0


@dataclass
class ErrorConfigParams:
    """错误模拟参数"""
    enabled: bool = False
    errors_per_8bars: int = 1
    wrong_note: bool = True
    miss_note: bool = True
    extra_note: bool = False
    pause_error: bool = False
    pause_min_ms: int = 100
    pause_max_ms: int = 300


@dataclass
class InputManagerParams:
    """输入管理器参数"""
    backend: str = "sendinput"
    min_press_interval_ms: float = 2.0
    min_hold_time_ms: float = 8.0
    post_release_delay_ms: float = 1.0
    key_timeout_ms: float = 5000.0
    enable_focus_monitor: bool = True
    focus_check_interval_ms: int = 100


@dataclass
class SettingsSchema:
    """完整设置 Schema"""
    # 版本
    version: int = SETTINGS_VERSION

    # 基本设置
    language: str = "简体中文"
    root_note: int = 60  # Middle C
    octave_shift: int = 0
    transpose: int = 0
    speed: float = 1.0
    press_ms: int = 25
    countdown_sec: int = 2
    keyboard_preset: str = "21-key"
    use_midi_duration: bool = False

    # 音效设置
    play_sound: bool = False
    soundfont_path: str = ""
    instrument: str = "Piano"
    velocity: int = 90

    # 风格设置
    input_style: str = "mechanical"
    custom_styles: Dict[str, Dict] = field(default_factory=dict)

    # 错误模拟
    error_config: ErrorConfigParams = field(default_factory=ErrorConfigParams)

    # 输入管理器
    input_manager: InputManagerParams = field(default_factory=InputManagerParams)

    # 调试
    enable_diagnostics: bool = False

    # 文件路径（不导出）
    last_midi_path: str = ""

    # 元数据
    created_at: str = ""
    modified_at: str = ""


# ============== 内置预设 ==============

BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "fast_precise": {
        "name_en": "Fast & Precise",
        "name_zh": "快速精准",
        "description_en": "Minimal latency, mechanical timing",
        "description_zh": "最低延迟，机械精准",
        "settings": {
            "input_style": "mechanical",
            "press_ms": 15,
            "use_midi_duration": False,
            "input_manager": {
                "min_press_interval_ms": 1.0,
                "min_hold_time_ms": 6.0,
                "post_release_delay_ms": 0.5,
            },
            "error_config": {"enabled": False},
        }
    },
    "natural_flow": {
        "name_en": "Natural Flow",
        "name_zh": "自然流畅",
        "description_en": "Human-like timing variations",
        "description_zh": "人性化时间变化",
        "settings": {
            "input_style": "natural",
            "press_ms": 30,
            "use_midi_duration": True,
            "input_manager": {
                "min_press_interval_ms": 2.0,
                "min_hold_time_ms": 8.0,
                "post_release_delay_ms": 1.0,
            },
            "error_config": {"enabled": False},
        }
    },
    "stable_compat": {
        "name_en": "Stable & Compatible",
        "name_zh": "稳定兼容",
        "description_en": "Maximum compatibility, longer delays",
        "description_zh": "最大兼容性，较长延迟",
        "settings": {
            "input_style": "mechanical",
            "press_ms": 50,
            "use_midi_duration": False,
            "input_manager": {
                "min_press_interval_ms": 5.0,
                "min_hold_time_ms": 15.0,
                "post_release_delay_ms": 3.0,
            },
            "error_config": {"enabled": False},
        }
    },
    "expressive_human": {
        "name_en": "Expressive Human",
        "name_zh": "富有感情",
        "description_en": "Maximum humanization with occasional errors",
        "description_zh": "最大人性化，偶尔出错",
        "settings": {
            "input_style": "expressive",
            "press_ms": 35,
            "use_midi_duration": True,
            "input_manager": {
                "min_press_interval_ms": 2.0,
                "min_hold_time_ms": 10.0,
                "post_release_delay_ms": 1.5,
            },
            "error_config": {
                "enabled": True,
                "errors_per_8bars": 1,
                "wrong_note": True,
                "miss_note": True,
            },
        }
    },
    "21key_default": {
        "name_en": "21-Key Default",
        "name_zh": "21键默认",
        "description_en": "Optimized for 21-key (diatonic) layout",
        "description_zh": "21键全音布局优化",
        "settings": {
            "keyboard_preset": "21-key",
            "input_style": "natural",
            "press_ms": 25,
        }
    },
    "36key_default": {
        "name_en": "36-Key Default",
        "name_zh": "36键默认",
        "description_en": "Optimized for 36-key (chromatic) layout",
        "description_zh": "36键半音布局优化",
        "settings": {
            "keyboard_preset": "36-key",
            "input_style": "natural",
            "press_ms": 25,
        }
    },
}


# ============== Settings Manager ==============

class SettingsManager:
    """设置管理器"""

    def __init__(self, settings_file: str):
        self.settings_file = settings_file
        self.settings = SettingsSchema()
        self._dirty = False

    def get_default_settings(self) -> SettingsSchema:
        """获取默认设置"""
        s = SettingsSchema()
        s.created_at = datetime.now().isoformat()
        s.modified_at = s.created_at
        return s

    def load(self) -> bool:
        """加载设置，返回是否成功"""
        if not os.path.exists(self.settings_file):
            self.settings = self.get_default_settings()
            return False

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 版本迁移
            data = self._migrate(data)

            # 应用到 schema
            self.settings = self._dict_to_schema(data)
            return True

        except Exception as e:
            print(f"[WARN] Failed to load settings: {e}")
            self.settings = self.get_default_settings()
            return False

    def save(self) -> bool:
        """保存设置，返回是否成功"""
        try:
            self.settings.modified_at = datetime.now().isoformat()
            data = self._schema_to_dict(self.settings)

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._dirty = False
            return True

        except Exception as e:
            print(f"[ERROR] Failed to save settings: {e}")
            return False

    def export_to_file(self, filepath: str) -> bool:
        """导出设置到文件"""
        try:
            data = self._schema_to_dict(self.settings)
            # 移除不应导出的字段
            data.pop('last_midi_path', None)
            data['_exported_at'] = datetime.now().isoformat()
            data['_export_version'] = SETTINGS_VERSION

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ERROR] Export failed: {e}")
            return False

    def import_from_file(self, filepath: str) -> Tuple[bool, str]:
        """从文件导入设置，返回 (成功, 消息)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 验证版本
            version = data.get('version', data.get('_export_version', 1))
            if version > SETTINGS_VERSION:
                return False, f"Settings version {version} is newer than supported {SETTINGS_VERSION}"

            # 迁移并应用
            data = self._migrate(data)
            self.settings = self._dict_to_schema(data)
            self._dirty = True

            return True, f"Imported successfully (version {version})"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Import failed: {e}"

    def export_to_clipboard(self) -> str:
        """导出设置到剪贴板格式"""
        data = self._schema_to_dict(self.settings)
        data.pop('last_midi_path', None)
        data['_exported_at'] = datetime.now().isoformat()
        return json.dumps(data, indent=2, ensure_ascii=False)

    def import_from_clipboard(self, text: str) -> Tuple[bool, str]:
        """从剪贴板文本导入设置"""
        try:
            data = json.loads(text)
            data = self._migrate(data)
            self.settings = self._dict_to_schema(data)
            self._dirty = True
            return True, "Imported from clipboard"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Import failed: {e}"

    def apply_preset(self, preset_name: str) -> bool:
        """应用预设"""
        if preset_name not in BUILTIN_PRESETS:
            return False

        preset = BUILTIN_PRESETS[preset_name]
        preset_settings = preset.get('settings', {})

        # 深度合并
        self._merge_dict(self._schema_to_dict(self.settings), preset_settings)
        self._dirty = True
        return True

    def reset_to_defaults(self):
        """重置为默认设置"""
        self.settings = self.get_default_settings()
        self._dirty = True

    def get_preset_list(self) -> List[Dict[str, str]]:
        """获取预设列表"""
        result = []
        for key, preset in BUILTIN_PRESETS.items():
            result.append({
                'key': key,
                'name_en': preset['name_en'],
                'name_zh': preset['name_zh'],
                'description_en': preset['description_en'],
                'description_zh': preset['description_zh'],
            })
        return result

    def validate(self) -> List[str]:
        """验证设置，返回错误列表"""
        errors = []
        s = self.settings

        # 基本范围检查
        if s.speed < 0.1 or s.speed > 10.0:
            errors.append(f"Speed {s.speed} out of range [0.1, 10.0]")
        if s.press_ms < 5 or s.press_ms > 500:
            errors.append(f"Press duration {s.press_ms}ms out of range [5, 500]")
        if s.velocity < 1 or s.velocity > 127:
            errors.append(f"Velocity {s.velocity} out of range [1, 127]")
        if s.countdown_sec < 0 or s.countdown_sec > 30:
            errors.append(f"Countdown {s.countdown_sec}s out of range [0, 30]")
        if s.keyboard_preset not in ("21-key", "36-key"):
            errors.append(f"Unknown keyboard preset: {s.keyboard_preset}")

        # 输入管理器参数
        im = s.input_manager
        if im.min_hold_time_ms < 1 or im.min_hold_time_ms > 100:
            errors.append(f"Min hold time {im.min_hold_time_ms}ms out of range [1, 100]")

        return errors

    # ============== 私有方法 ==============

    def _migrate(self, data: Dict) -> Dict:
        """版本迁移"""
        version = data.get('version', 1)

        # v1 -> v2: 添加 input_manager 配置
        if version < 2:
            data['input_manager'] = {
                'backend': 'sendinput',
                'min_press_interval_ms': 2.0,
                'min_hold_time_ms': 8.0,
            }
            data['version'] = 2

        # v2 -> v3: 添加焦点监控配置
        if version < 3:
            im = data.get('input_manager', {})
            im['enable_focus_monitor'] = True
            im['focus_check_interval_ms'] = 100
            data['input_manager'] = im
            data['version'] = 3

        return data

    def _schema_to_dict(self, schema: SettingsSchema) -> Dict:
        """Schema 转字典"""
        result = {}
        for key, value in schema.__dict__.items():
            if hasattr(value, '__dict__') and not isinstance(value, dict):
                result[key] = self._schema_to_dict(value)
            else:
                result[key] = value
        return result

    def _dict_to_schema(self, data: Dict) -> SettingsSchema:
        """字典转 Schema（带默认值填充）"""
        s = SettingsSchema()

        # 简单字段
        for key in ['version', 'language', 'root_note', 'octave_shift', 'transpose',
                    'speed', 'press_ms', 'countdown_sec', 'keyboard_preset',
                    'use_midi_duration', 'play_sound', 'soundfont_path', 'instrument',
                    'velocity', 'input_style', 'enable_diagnostics', 'last_midi_path',
                    'created_at', 'modified_at']:
            if key in data:
                setattr(s, key, data[key])

        # 复杂字段
        if 'custom_styles' in data:
            s.custom_styles = data['custom_styles']

        if 'error_config' in data:
            ec = data['error_config']
            s.error_config = ErrorConfigParams(
                enabled=ec.get('enabled', False),
                errors_per_8bars=ec.get('errors_per_8bars', 1),
                wrong_note=ec.get('wrong_note', True),
                miss_note=ec.get('miss_note', True),
                extra_note=ec.get('extra_note', False),
                pause_error=ec.get('pause_error', False),
                pause_min_ms=ec.get('pause_min_ms', 100),
                pause_max_ms=ec.get('pause_max_ms', 300),
            )

        if 'input_manager' in data:
            im = data['input_manager']
            s.input_manager = InputManagerParams(
                backend=im.get('backend', 'sendinput'),
                min_press_interval_ms=im.get('min_press_interval_ms', 2.0),
                min_hold_time_ms=im.get('min_hold_time_ms', 8.0),
                post_release_delay_ms=im.get('post_release_delay_ms', 1.0),
                key_timeout_ms=im.get('key_timeout_ms', 5000.0),
                enable_focus_monitor=im.get('enable_focus_monitor', True),
                focus_check_interval_ms=im.get('focus_check_interval_ms', 100),
            )

        return s

    def _merge_dict(self, target: Dict, source: Dict):
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value


# ============== 工厂函数 ==============

def create_settings_manager(settings_file: str) -> SettingsManager:
    """创建设置管理器并加载设置"""
    manager = SettingsManager(settings_file)
    manager.load()
    return manager
