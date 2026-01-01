# Plugin Interface Design

> Step 3 产出：插件接口（最小 API）

## 设计目标

1. **最小化**: 插件只需实现 `on_load()`
2. **可扩展**: 可选实现生命周期钩子
3. **安全**: 插件异常不影响核心
4. **可调试**: 提供日志和诊断能力

## 核心接口

### Plugin 基类

```python
# core/plugin.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .app import Application
    from .events import EventBus
    from .config import ConfigManager

class Plugin(ABC):
    """插件基类

    最小实现:
        class MyPlugin(Plugin):
            name = "my_plugin"

            def on_load(self, app):
                # 订阅事件、注册功能
                pass

    完整实现:
        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "1.0.0"
            description = "My awesome plugin"
            dependencies = ["other_plugin"]  # 依赖的其他插件

            def on_load(self, app):
                self.app = app
                self.events = app.events
                self.config = app.config

                # 订阅事件
                self.events.subscribe(EventType.PLAY_START, self.on_play_start)

            def on_unload(self):
                # 清理资源
                self.events.unsubscribe(EventType.PLAY_START, self.on_play_start)

            def on_config_changed(self, domain, key, value):
                # 响应配置变更
                pass

            def on_play_start(self, **kwargs):
                # 处理播放开始事件
                pass
    """

    # === 必需属性 ===
    name: str  # 插件唯一标识符 (snake_case)

    # === 可选属性 ===
    version: str = "1.0.0"
    description: str = ""
    dependencies: list = []  # 依赖的其他插件名称

    # === 运行时属性 (由 Application 设置) ===
    _app: Optional["Application"] = None

    @property
    def app(self) -> "Application":
        """获取 Application 实例"""
        if self._app is None:
            raise RuntimeError(f"Plugin {self.name} not loaded")
        return self._app

    @property
    def events(self) -> "EventBus":
        """快捷访问事件总线"""
        return self.app.events

    @property
    def config(self) -> "ConfigManager":
        """快捷访问配置管理器"""
        return self.app.config

    # === 生命周期方法 ===

    @abstractmethod
    def on_load(self, app: "Application") -> None:
        """插件加载时调用

        在这里:
        - 订阅事件
        - 注册 UI 组件
        - 初始化资源

        Args:
            app: Application 实例
        """
        pass

    def on_unload(self) -> None:
        """插件卸载时调用 (可选)

        在这里:
        - 取消订阅事件
        - 清理资源
        - 保存状态
        """
        pass

    def on_config_changed(self, domain: str, key: str, value: Any) -> None:
        """配置变更时调用 (可选)

        Args:
            domain: 配置域 (playback/sound/error/eight_bar)
            key: 配置键
            value: 新值
        """
        pass

    # === 辅助方法 ===

    def log(self, level: str, message: str) -> None:
        """输出日志

        Args:
            level: 日志级别 (debug/info/warn/error)
            message: 日志消息
        """
        from .events import EventType
        self.events.publish(EventType.LOG_MESSAGE, level, f"[{self.name}] {message}")

    def log_info(self, message: str) -> None:
        """输出 INFO 级别日志"""
        self.log("info", message)

    def log_warn(self, message: str) -> None:
        """输出 WARN 级别日志"""
        self.log("warn", message)

    def log_error(self, message: str) -> None:
        """输出 ERROR 级别日志"""
        self.log("error", message)
```

### UIPlugin 扩展

```python
# core/plugin.py (续)

class UIPlugin(Plugin):
    """UI 插件扩展

    用于需要在主窗口注册 UI 组件的插件。

    示例:
        class ErrorsUIPlugin(UIPlugin):
            name = "errors_ui"

            def on_load(self, app):
                super().on_load(app)

            def create_tab(self) -> Optional[QWidget]:
                return ErrorsTabWidget(self.app)

            def get_tab_info(self) -> Tuple[str, str]:
                return ("errors", "tab_errors")  # (id, translation_key)
    """

    def create_tab(self) -> Optional["QWidget"]:
        """创建 Tab 面板 (可选)

        Returns:
            QWidget 或 None
        """
        return None

    def get_tab_info(self) -> tuple:
        """获取 Tab 信息

        Returns:
            (tab_id, translation_key)
        """
        return ("", "")

    def create_floating_controls(self) -> Optional["QWidget"]:
        """创建悬浮窗控件 (可选)

        Returns:
            QWidget 或 None
        """
        return None
```

### PlayerPlugin 扩展

```python
# core/plugin.py (续)

class PlayerPlugin(Plugin):
    """播放器插件扩展

    用于修改播放行为的插件 (如错误模拟、8-bar 变速)。

    示例:
        class ErrorsPlugin(PlayerPlugin):
            name = "errors"
            priority = 100  # 处理优先级

            def on_load(self, app):
                super().on_load(app)

            def process_note(self, note, time, duration, context):
                if self.should_skip_note():
                    return None  # 跳过此音符
                return note, time, duration

            def process_timing(self, time, context):
                return time + self.get_timing_variation()
    """

    # 处理优先级 (数字越小越先执行)
    priority: int = 100

    def process_note(
        self,
        note: int,
        time: float,
        duration: float,
        context: dict
    ) -> Optional[tuple]:
        """处理单个音符 (可选)

        Args:
            note: MIDI 音符号
            time: 播放时间 (秒)
            duration: 持续时间 (秒)
            context: 上下文信息 (bar_index, beat_index 等)

        Returns:
            (note, time, duration) 或 None (跳过此音符)
        """
        return note, time, duration

    def process_timing(self, time: float, context: dict) -> float:
        """处理时间 (可选)

        用于添加时序偏移、变速等。

        Args:
            time: 原始时间
            context: 上下文信息

        Returns:
            修改后的时间
        """
        return time

    def on_bar_start(self, bar_index: int, bar_duration: float) -> None:
        """小节开始时调用 (可选)"""
        pass

    def on_bar_end(self, bar_index: int) -> None:
        """小节结束时调用 (可选)"""
        pass
```

---

## Application 类

```python
# core/app.py

import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Type, Optional, Any
from dataclasses import dataclass

from .events import EventBus, EventType
from .config import ConfigManager
from .plugin import Plugin, UIPlugin, PlayerPlugin


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    status: str  # "loaded" / "failed" / "disabled"
    error: Optional[str] = None


class Application:
    """应用主类

    职责:
    - 插件发现与加载
    - 事件总线管理
    - 配置管理
    - 生命周期管理

    使用:
        app = Application()
        app.discover_plugins("plugins/")
        app.load_all_plugins()
        app.run()  # 启动 Qt 事件循环
    """

    _instance: Optional["Application"] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # 核心组件
        self.events = EventBus()
        self.config = ConfigManager()

        # 插件管理
        self._plugin_classes: Dict[str, Type[Plugin]] = {}
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}

        # UI 组件 (延迟初始化)
        self._main_window = None
        self._floating = None

    @classmethod
    def get_instance(cls) -> "Application":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # === 插件管理 ===

    def discover_plugins(self, plugin_dir: str = "plugins") -> List[str]:
        """发现插件

        扫描指定目录下的 Python 文件，查找 Plugin 子类。

        Args:
            plugin_dir: 插件目录路径

        Returns:
            发现的插件名称列表
        """
        discovered = []
        plugin_path = Path(plugin_dir)

        if not plugin_path.exists():
            self.events.publish(EventType.LOG_MESSAGE, "warn", f"Plugin directory not found: {plugin_dir}")
            return discovered

        for file in sorted(plugin_path.glob("*.py")):
            if file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Plugin) and obj not in (Plugin, UIPlugin, PlayerPlugin):
                        if hasattr(obj, "name") and obj.name:
                            self._plugin_classes[obj.name] = obj
                            discovered.append(obj.name)
                            self.events.publish(EventType.LOG_MESSAGE, "debug", f"Discovered plugin: {obj.name}")

            except Exception as e:
                self.events.publish(EventType.LOG_MESSAGE, "warn", f"Failed to scan {file.name}: {e}")

        return discovered

    def register_plugin_class(self, plugin_class: Type[Plugin]) -> None:
        """手动注册插件类"""
        if hasattr(plugin_class, "name") and plugin_class.name:
            self._plugin_classes[plugin_class.name] = plugin_class

    def load_plugin(self, name: str) -> bool:
        """加载单个插件

        Args:
            name: 插件名称

        Returns:
            是否加载成功
        """
        if name in self._plugins:
            return True  # 已加载

        if name not in self._plugin_classes:
            self._plugin_info[name] = PluginInfo(
                name=name,
                version="",
                description="",
                status="failed",
                error="Plugin class not found"
            )
            return False

        plugin_class = self._plugin_classes[name]

        # 检查依赖
        for dep in getattr(plugin_class, "dependencies", []):
            if dep not in self._plugins:
                if not self.load_plugin(dep):
                    self._plugin_info[name] = PluginInfo(
                        name=name,
                        version=getattr(plugin_class, "version", "1.0.0"),
                        description=getattr(plugin_class, "description", ""),
                        status="failed",
                        error=f"Dependency not met: {dep}"
                    )
                    return False

        try:
            plugin = plugin_class()
            plugin._app = self
            plugin.on_load(self)

            self._plugins[name] = plugin
            self._plugin_info[name] = PluginInfo(
                name=name,
                version=getattr(plugin, "version", "1.0.0"),
                description=getattr(plugin, "description", ""),
                status="loaded"
            )

            self.events.publish(EventType.LOG_MESSAGE, "info", f"Plugin loaded: {name}")
            return True

        except Exception as e:
            self._plugin_info[name] = PluginInfo(
                name=name,
                version=getattr(plugin_class, "version", "1.0.0"),
                description=getattr(plugin_class, "description", ""),
                status="failed",
                error=str(e)
            )
            self.events.publish(EventType.LOG_MESSAGE, "warn", f"Plugin failed: {name}: {e}")
            return False

    def unload_plugin(self, name: str) -> bool:
        """卸载插件"""
        if name not in self._plugins:
            return False

        try:
            plugin = self._plugins[name]
            plugin.on_unload()
            del self._plugins[name]

            if name in self._plugin_info:
                self._plugin_info[name].status = "disabled"

            self.events.publish(EventType.LOG_MESSAGE, "info", f"Plugin unloaded: {name}")
            return True

        except Exception as e:
            self.events.publish(EventType.LOG_MESSAGE, "warn", f"Plugin unload failed: {name}: {e}")
            return False

    def load_all_plugins(self) -> Dict[str, bool]:
        """加载所有已发现的插件

        Returns:
            {plugin_name: success}
        """
        results = {}
        for name in sorted(self._plugin_classes.keys()):
            results[name] = self.load_plugin(name)
        return results

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取已加载的插件"""
        return self._plugins.get(name)

    def get_plugins_by_type(self, plugin_type: Type[Plugin]) -> List[Plugin]:
        """获取指定类型的所有插件"""
        return [p for p in self._plugins.values() if isinstance(p, plugin_type)]

    def get_player_plugins(self) -> List[PlayerPlugin]:
        """获取所有播放器插件 (按优先级排序)"""
        plugins = self.get_plugins_by_type(PlayerPlugin)
        return sorted(plugins, key=lambda p: p.priority)

    def get_ui_plugins(self) -> List[UIPlugin]:
        """获取所有 UI 插件"""
        return self.get_plugins_by_type(UIPlugin)

    def get_all_plugin_info(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        return list(self._plugin_info.values())

    # === 配置变更通知 ===

    def notify_config_changed(self, domain: str, key: str, value: Any) -> None:
        """通知所有插件配置已变更"""
        for plugin in self._plugins.values():
            try:
                plugin.on_config_changed(domain, key, value)
            except Exception as e:
                self.events.publish(EventType.LOG_MESSAGE, "warn",
                    f"Plugin {plugin.name} config_changed error: {e}")

        self.events.publish(EventType.CONFIG_CHANGED, domain, key, value)

    # === 应用生命周期 ===

    def run(self) -> int:
        """启动应用

        Returns:
            exit code
        """
        from PyQt6.QtWidgets import QApplication
        import sys

        qt_app = QApplication(sys.argv)

        # 创建主窗口 (延迟导入)
        from ui.main_window import MainWindow
        self._main_window = MainWindow(self)
        self._main_window.show()

        return qt_app.exec()

    def quit(self) -> None:
        """退出应用"""
        # 卸载所有插件
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)

        # 退出 Qt
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
```

---

## 示例插件

### 错误模拟插件

```python
# plugins/errors.py

from core.plugin import PlayerPlugin
from core.events import EventType
import random

class ErrorsPlugin(PlayerPlugin):
    """错误模拟插件

    在播放过程中随机引入人为错误:
    - wrong_note: 弹错音 (相邻音)
    - miss_note: 漏音
    - extra_note: 多弹一个音
    - pause: 断音/卡顿
    """

    name = "errors"
    version = "1.0.0"
    description = "Human-like error simulation"
    priority = 50  # 在其他处理之后执行

    def on_load(self, app):
        self._enabled = False
        self._errors_per_8bars = 1
        self._error_types = ["wrong_note", "miss_note", "extra_note", "pause"]
        self._planned_errors = []
        self._current_bar = -1

        # 从配置加载
        error_config = app.config.get_domain("error")
        if error_config:
            self._enabled = error_config.get("enabled", False)
            self._errors_per_8bars = error_config.get("errors_per_8bars", 1)

        self.log_info("Loaded")

    def on_config_changed(self, domain, key, value):
        if domain == "error":
            if key == "enabled":
                self._enabled = value
            elif key == "errors_per_8bars":
                self._errors_per_8bars = value

    def on_bar_start(self, bar_index, bar_duration):
        # 每 8 小节规划错误
        if bar_index % 8 == 0:
            self._planned_errors = self._plan_errors()

    def process_note(self, note, time, duration, context):
        if not self._enabled:
            return note, time, duration

        # 检查是否有计划的错误
        bar_position = context.get("bar_position", 0)
        for error_type, error_pos in self._planned_errors:
            if abs(bar_position - error_pos) < 0.05:
                return self._apply_error(error_type, note, time, duration)

        return note, time, duration

    def _plan_errors(self):
        """规划 8 小节内的错误"""
        if not self._enabled or self._errors_per_8bars <= 0:
            return []

        errors = []
        for _ in range(self._errors_per_8bars):
            error_type = random.choice(self._error_types)
            position = random.random()  # 0.0 - 1.0
            errors.append((error_type, position))

        return sorted(errors, key=lambda x: x[1])

    def _apply_error(self, error_type, note, time, duration):
        if error_type == "miss_note":
            return None  # 跳过此音符
        elif error_type == "wrong_note":
            offset = random.choice([-1, 1])
            return note + offset, time, duration
        elif error_type == "pause":
            pause_ms = random.randint(100, 500)
            return note, time + pause_ms / 1000.0, duration
        else:
            return note, time, duration
```

### 8-Bar 变速插件

```python
# plugins/eight_bar.py

from core.plugin import PlayerPlugin
from core.events import EventType
import math

class EightBarPlugin(PlayerPlugin):
    """8-Bar 变速插件

    根据小节位置调整播放速度和时序:
    - tempo_warp: 平滑速度变化
    - beat_lock: 锁定节拍位置
    """

    name = "eight_bar"
    version = "1.0.0"
    description = "8-bar tempo variation"
    priority = 30  # 在错误模拟之前执行

    def on_load(self, app):
        self._enabled = False
        self._mode = "warp"  # warp / beat_lock
        self._speed_variation = 0.0
        self._timing_variation = 0.0

        # 从配置加载
        config = app.config.get_domain("eight_bar")
        if config:
            self._enabled = config.get("enabled", False)
            self._mode = config.get("mode", "warp")
            self._speed_variation = config.get("speed_variation", 0.0)
            self._timing_variation = config.get("timing_variation", 0.0)

        self.log_info("Loaded")

    def on_config_changed(self, domain, key, value):
        if domain == "eight_bar":
            setattr(self, f"_{key}", value)

    def process_timing(self, time, context):
        if not self._enabled:
            return time

        bar_position = context.get("bar_position", 0)  # 0.0 - 1.0 in 8-bar group

        if self._mode == "warp":
            # 正弦波速度变化
            warp = math.sin(bar_position * 2 * math.pi) * self._speed_variation
            return time * (1.0 + warp)
        elif self._mode == "beat_lock":
            # 锁定到最近节拍
            beat_duration = context.get("beat_duration", 0.5)
            nearest_beat = round(time / beat_duration) * beat_duration
            return nearest_beat

        return time
```

---

## 验收命令

```python
# 最小自检脚本
# 保存为: LyreAutoPlayer/test_plugin_api.py

def test_plugin_api():
    """验证插件 API 可用"""

    # 1. 导入测试
    from core.plugin import Plugin, UIPlugin, PlayerPlugin
    from core.app import Application
    from core.events import EventBus, EventType

    print("[OK] Imports successful")

    # 2. 创建应用
    app = Application()
    assert app.events is not None
    assert app.config is not None
    print("[OK] Application created")

    # 3. 定义测试插件
    class TestPlugin(Plugin):
        name = "test"
        loaded = False

        def on_load(self, app):
            self.loaded = True

        def on_unload(self):
            self.loaded = False

    # 4. 注册并加载
    app.register_plugin_class(TestPlugin)
    assert app.load_plugin("test")
    print("[OK] Plugin loaded")

    # 5. 验证状态
    plugin = app.get_plugin("test")
    assert plugin is not None
    assert plugin.loaded
    print("[OK] Plugin state verified")

    # 6. 卸载
    assert app.unload_plugin("test")
    assert not plugin.loaded
    print("[OK] Plugin unloaded")

    print("\n=== All tests passed ===")

if __name__ == "__main__":
    test_plugin_api()
```

---

*生成时间: 2026-01-02*
*Plan Step 3 完成*
