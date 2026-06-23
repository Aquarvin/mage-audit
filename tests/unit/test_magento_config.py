"""Tests for Magento XML config parser."""

from pathlib import Path

from src.frameworks.magento import MagentoConfigParser

SAMPLE_MODULE = Path("notebooks/samples/sample-module")


class TestMagentoConfigParser:
    """Test parsing of Magento XML configs."""

    def setup_method(self):
        self.parser = MagentoConfigParser()

    def test_parse_module_xml(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        assert config.module_info is not None
        assert config.module_info.name == "Vendor_OrderManager"
        assert config.module_info.setup_version == "1.0.0"

    def test_module_dependencies(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        deps = config.module_info.dependencies
        assert "Magento_Sales" in deps
        assert "Magento_Catalog" in deps

    def test_parse_plugins(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        assert len(config.plugins) == 2

        plugin_names = [p.name for p in config.plugins]
        assert "vendor_order_manager_order_save_plugin" in plugin_names

        save_plugin = next(p for p in config.plugins if "save" in p.name)
        assert (
            save_plugin.target_class == "Magento\\Sales\\Api\\OrderRepositoryInterface"
        )
        assert (
            save_plugin.plugin_class == "Vendor\\OrderManager\\Plugin\\OrderSavePlugin"
        )
        assert save_plugin.sort_order == 10
        assert save_plugin.disabled is False

    def test_parse_preferences(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        assert len(config.preferences) == 2

        pref = next(p for p in config.preferences if "OrderProcessor" in p.interface)
        assert pref.interface == "Vendor\\OrderManager\\Api\\OrderProcessorInterface"
        assert pref.implementation == "Vendor\\OrderManager\\Model\\OrderProcessor"

    def test_parse_observers(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        assert len(config.observers) == 3

        events = [o.event_name for o in config.observers]
        assert "sales_order_place_after" in events
        assert "sales_order_save_before" in events
        assert "checkout_submit_all_after" in events

    def test_observer_details(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        obs = next(
            o for o in config.observers if o.event_name == "sales_order_place_after"
        )
        assert obs.instance_class == "Vendor\\OrderManager\\Observer\\OrderPlaceAfter"
        assert obs.method == "execute"
        assert obs.disabled is False

    def test_parse_virtual_types(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        assert len(config.virtual_types) == 1

        vt = config.virtual_types[0]
        assert "VirtualLogger" in vt.name
        assert "Monolog" in vt.base_type
        assert vt.arguments.get("name") == "order_manager"

    def test_summary(self):
        config = self.parser.parse_module_directory(SAMPLE_MODULE)
        summary = config.summary
        assert "Vendor_OrderManager" in summary
        assert "Plugins: 2" in summary
        assert "Observers: 3" in summary

    def test_nonexistent_directory(self):
        config = self.parser.parse_module_directory("/nonexistent/path")
        assert config.module_info is None
        assert config.plugins == []
        assert config.observers == []

    def test_empty_directory(self, tmp_path):
        """Directory with no etc/ folder."""
        config = self.parser.parse_module_directory(tmp_path)
        assert config.module_info is None
