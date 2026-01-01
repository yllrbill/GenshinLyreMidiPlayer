"""
Style Plugin Loader

Dynamically loads style plugins from the plugins/ directory.
Each plugin should have a register(registry) function.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional, List

from .registry import StyleRegistry, create_default_registry


def load_plugin(plugin_path: Path, registry: StyleRegistry) -> bool:
    """
    Load a single plugin file.

    Args:
        plugin_path: Path to the .py plugin file
        registry: StyleRegistry to register styles into

    Returns:
        True if loaded successfully, False otherwise
    """
    if not plugin_path.exists() or not plugin_path.suffix == ".py":
        return False

    module_name = f"styles.plugins.{plugin_path.stem}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        if spec is None or spec.loader is None:
            return False

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Call the register function if it exists
        if hasattr(module, "register"):
            module.register(registry)
            return True
        else:
            print(f"[WARN] Plugin {plugin_path.name} has no register() function")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to load plugin {plugin_path.name}: {e}")
        return False


def load_plugins(registry: StyleRegistry, plugin_dir: Path) -> List[str]:
    """
    Load all plugins from a directory.

    Args:
        registry: StyleRegistry to register styles into
        plugin_dir: Directory containing .py plugin files

    Returns:
        List of successfully loaded plugin names
    """
    loaded = []

    if not plugin_dir.exists():
        return loaded

    # Sort for deterministic load order
    for p in sorted(plugin_dir.glob("*.py")):
        # Skip __init__.py and other special files
        if p.name.startswith("_"):
            continue

        if load_plugin(p, registry):
            loaded.append(p.stem)

    return loaded


# Global registry instance
_global_registry: Optional[StyleRegistry] = None


def get_default_registry() -> StyleRegistry:
    """
    Get or create the global default registry.

    Loads built-in styles and plugins from the default location.
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = create_default_registry()

        # Load plugins from styles/plugins/
        plugin_dir = Path(__file__).parent / "plugins"
        loaded = load_plugins(_global_registry, plugin_dir)
        if loaded:
            print(f"[INFO] Loaded style plugins: {', '.join(loaded)}")

    return _global_registry


def reload_plugins() -> List[str]:
    """
    Reload all plugins (useful for development).

    Returns:
        List of loaded plugin names
    """
    global _global_registry

    if _global_registry is None:
        get_default_registry()
        return []

    # Remove non-builtin styles
    for name in list(_global_registry.get_names()):
        style = _global_registry.get(name)
        if style and not style.builtin:
            _global_registry.unregister(name)

    # Reload plugins
    plugin_dir = Path(__file__).parent / "plugins"
    return load_plugins(_global_registry, plugin_dir)
