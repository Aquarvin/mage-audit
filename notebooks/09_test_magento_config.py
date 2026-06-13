"""Test Magento config parser on sample module."""

from src.frameworks.magento import MagentoConfigParser

parser = MagentoConfigParser()
config = parser.parse_module_directory("notebooks/samples/sample-module")

print(f"=== {config.summary} ===\n")

# Module info
if config.module_info:
    print(f"Module: {config.module_info.name}")
    print(f"Version: {config.module_info.setup_version}")
    print(f"Dependencies: {config.module_info.dependencies}")
    print()

# Preferences
print(f"--- Preferences ({len(config.preferences)}) ---")
for pref in config.preferences:
    print(f"  {pref.interface}")
    print(f"    → {pref.implementation}")
print()

# Plugins
print(f"--- Plugins ({len(config.plugins)}) ---")
for plugin in config.plugins:
    status = " [DISABLED]" if plugin.disabled else ""
    print(f"  {plugin.name} (order: {plugin.sort_order}){status}")
    print(f"    Target: {plugin.target_class}")
    print(f"    Plugin: {plugin.plugin_class}")
print()

# Observers
print(f"--- Observers ({len(config.observers)}) ---")
for obs in config.observers:
    status = " [DISABLED]" if obs.disabled else ""
    print(f"  Event: {obs.event_name}{status}")
    print(f"    Observer: {obs.observer_name}")
    print(f"    Class: {obs.instance_class}::{obs.method}()")
print()

# Virtual Types
print(f"--- Virtual Types ({len(config.virtual_types)}) ---")
for vt in config.virtual_types:
    print(f"  {vt.name}")
    print(f"    Base: {vt.base_type}")
    if vt.arguments:
        print(f"    Args: {vt.arguments}")
