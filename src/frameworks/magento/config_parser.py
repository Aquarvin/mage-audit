"""Parser for Magento XML configuration files.

Extracts plugins, preferences, observers, virtual types,
and module metadata from di.xml, events.xml, module.xml.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

import structlog

from src.frameworks.magento.types import (
    MagentoModuleConfig,
    MagentoModuleInfo,
    MagentoObserver,
    MagentoPlugin,
    MagentoPreference,
    MagentoVirtualType,
)

logger = structlog.get_logger()


class MagentoConfigParser:
    """Parses Magento module XML configuration files."""

    def parse_module_directory(self, module_path: str | Path) -> MagentoModuleConfig:
        """Parse all config files in a Magento module directory.

        Args:
            module_path: Path to the module root (contains etc/, Model/, etc.)

        Returns:
            MagentoModuleConfig with all parsed data.
        """
        module_path = Path(module_path)
        config = MagentoModuleConfig()

        etc_path = module_path / "etc"
        if not etc_path.exists():
            logger.warning("No etc/ directory found", path=str(module_path))
            return config

        # Parse module.xml
        module_xml = etc_path / "module.xml"
        if module_xml.exists():
            config.module_info = self._parse_module_xml(module_xml)

        # Parse di.xml (global scope)
        di_xml = etc_path / "di.xml"
        if di_xml.exists():
            plugins, preferences, virtual_types = self._parse_di_xml(di_xml)
            config.plugins.extend(plugins)
            config.preferences.extend(preferences)
            config.virtual_types.extend(virtual_types)

        # Parse area-scoped di.xml (frontend, adminhtml, webapi_rest, etc.)
        for area in ("frontend", "adminhtml", "webapi_rest", "webapi_soap", "crontab"):
            area_di = etc_path / area / "di.xml"
            if area_di.exists():
                plugins, preferences, virtual_types = self._parse_di_xml(area_di)
                # Tag with area scope
                for plugin in plugins:
                    plugin.name = f"[{area}] {plugin.name}"
                config.plugins.extend(plugins)
                config.preferences.extend(preferences)
                config.virtual_types.extend(virtual_types)

        # Parse events.xml (global scope)
        events_xml = etc_path / "events.xml"
        if events_xml.exists():
            config.observers.extend(self._parse_events_xml(events_xml))

        # Parse area-scoped events.xml
        for area in ("frontend", "adminhtml"):
            area_events = etc_path / area / "events.xml"
            if area_events.exists():
                observers = self._parse_events_xml(area_events)
                for obs in observers:
                    obs.observer_name = f"[{area}] {obs.observer_name}"
                config.observers.extend(observers)

        return config

    def _parse_module_xml(self, path: Path) -> MagentoModuleInfo | None:
        """Parse etc/module.xml for module name and dependencies."""
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            module_node = root.find("module")
            if module_node is None:
                return None

            name = module_node.get("name", "Unknown")
            version = module_node.get("setup_version")

            deps = []
            sequence = module_node.find("sequence")
            if sequence is not None:
                for dep in sequence.findall("module"):
                    dep_name = dep.get("name")
                    if dep_name:
                        deps.append(dep_name)

            logger.info("Parsed module.xml", module=name, dependencies=len(deps))
            return MagentoModuleInfo(
                name=name,
                setup_version=version,
                dependencies=deps,
            )

        except ET.ParseError as e:
            logger.error("Failed to parse module.xml", path=str(path), error=str(e))
            return None

    def _parse_di_xml(
        self, path: Path
    ) -> tuple[list[MagentoPlugin], list[MagentoPreference], list[MagentoVirtualType]]:
        """Parse di.xml for plugins, preferences, and virtual types."""
        plugins = []
        preferences = []
        virtual_types = []

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            # Preferences
            for pref_node in root.findall("preference"):
                interface = pref_node.get("for", "")
                impl = pref_node.get("type", "")
                if interface and impl:
                    preferences.append(
                        MagentoPreference(interface=interface, implementation=impl)
                    )

            # Plugins and type arguments
            for type_node in root.findall("type"):
                type_name = type_node.get("name", "")

                for plugin_node in type_node.findall("plugin"):
                    plugin_name = plugin_node.get("name", "")
                    plugin_type = plugin_node.get("type", "")
                    sort_order = int(plugin_node.get("sortOrder", "0"))
                    disabled = plugin_node.get("disabled", "false").lower() == "true"

                    if plugin_name and plugin_type:
                        plugins.append(
                            MagentoPlugin(
                                name=plugin_name,
                                target_class=type_name,
                                plugin_class=plugin_type,
                                sort_order=sort_order,
                                disabled=disabled,
                            )
                        )

            # Virtual types
            for vtype_node in root.findall("virtualType"):
                vtype_name = vtype_node.get("name", "")
                vtype_base = vtype_node.get("type", "")
                args = {}

                args_node = vtype_node.find("arguments")
                if args_node is not None:
                    for arg in args_node.findall("argument"):
                        arg_name = arg.get("name", "")
                        arg_value = arg.text or ""
                        if arg_name:
                            args[arg_name] = arg_value

                if vtype_name and vtype_base:
                    virtual_types.append(
                        MagentoVirtualType(
                            name=vtype_name,
                            base_type=vtype_base,
                            arguments=args,
                        )
                    )

            logger.info(
                "Parsed di.xml",
                path=str(path),
                plugins=len(plugins),
                preferences=len(preferences),
                virtual_types=len(virtual_types),
            )

        except ET.ParseError as e:
            logger.error("Failed to parse di.xml", path=str(path), error=str(e))

        return plugins, preferences, virtual_types

    def _parse_events_xml(self, path: Path) -> list[MagentoObserver]:
        """Parse events.xml for event observers."""
        observers = []

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            for event_node in root.findall("event"):
                event_name = event_node.get("name", "")

                for obs_node in event_node.findall("observer"):
                    obs_name = obs_node.get("name", "")
                    instance = obs_node.get("instance", "")
                    method = obs_node.get("method", "execute")
                    disabled = obs_node.get("disabled", "false").lower() == "true"

                    if obs_name and instance:
                        observers.append(
                            MagentoObserver(
                                event_name=event_name,
                                observer_name=obs_name,
                                instance_class=instance,
                                method=method,
                                disabled=disabled,
                            )
                        )

            logger.info(
                "Parsed events.xml",
                path=str(path),
                observers=len(observers),
            )

        except ET.ParseError as e:
            logger.error("Failed to parse events.xml", path=str(path), error=str(e))

        return observers
