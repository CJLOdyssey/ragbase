"""Tool plugin auto-discovery.

All modules in this directory are imported on startup,
triggering their self-registration with the ToolRegistry.
"""

import importlib
import pkgutil

__path__ = __path__

for _loader, _module_name, _is_pkg in pkgutil.iter_modules(__path__):
    if _module_name != "__init__":
        importlib.import_module(f"{__name__}.{_module_name}")
