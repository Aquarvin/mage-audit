"""Domain types for Magento module analysis."""

from dataclasses import dataclass, field


@dataclass
class MagentoPlugin:
    """A plugin (interceptor) defined in di.xml."""

    name: str
    target_class: str  # class being modified
    plugin_class: str  # class implementing the plugin
    sort_order: int = 0
    disabled: bool = False


@dataclass
class MagentoPreference:
    """A preference (interface → implementation mapping) from di.xml."""

    interface: str
    implementation: str


@dataclass
class MagentoObserver:
    """An event observer defined in events.xml."""

    event_name: str
    observer_name: str
    instance_class: str
    method: str = "execute"
    disabled: bool = False


@dataclass
class MagentoVirtualType:
    """A virtual type defined in di.xml."""

    name: str
    base_type: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass
class MagentoModuleInfo:
    """Parsed module metadata from module.xml."""

    name: str  # e.g. "Vendor_OrderManager"
    setup_version: str | None = None
    dependencies: list[str] = field(default_factory=list)  # sequence modules


@dataclass
class MagentoModuleConfig:
    """Complete parsed configuration of a Magento module."""

    module_info: MagentoModuleInfo | None = None
    plugins: list[MagentoPlugin] = field(default_factory=list)
    preferences: list[MagentoPreference] = field(default_factory=list)
    observers: list[MagentoObserver] = field(default_factory=list)
    virtual_types: list[MagentoVirtualType] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """Human-readable summary of the module config."""
        parts = []
        if self.module_info:
            parts.append(f"Module: {self.module_info.name}")
            if self.module_info.dependencies:
                parts.append(
                    f"Dependencies: {', '.join(self.module_info.dependencies)}"
                )
        parts.append(f"Plugins: {len(self.plugins)}")
        parts.append(f"Preferences: {len(self.preferences)}")
        parts.append(f"Observers: {len(self.observers)}")
        parts.append(f"Virtual Types: {len(self.virtual_types)}")
        return " | ".join(parts)
