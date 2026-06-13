"""Magento framework support."""

from src.frameworks.magento.config_parser import MagentoConfigParser
from src.frameworks.magento.indexer import MagentoModuleIndexer
from src.frameworks.magento.types import (
    MagentoModuleConfig,
    MagentoModuleInfo,
    MagentoObserver,
    MagentoPlugin,
    MagentoPreference,
    MagentoVirtualType,
)

__all__ = [
    "MagentoConfigParser",
    "MagentoModuleConfig",
    "MagentoModuleInfo",
    "MagentoModuleIndexer",
    "MagentoObserver",
    "MagentoPlugin",
    "MagentoPreference",
    "MagentoVirtualType",
]
