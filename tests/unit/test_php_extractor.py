"""Tests for PHP code extractor."""

from src.languages.php import PHPExtractor


class TestPHPExtractor:
    """Test tree-sitter PHP parsing."""

    def setup_method(self):
        self.extractor = PHPExtractor()

    def test_extract_simple_class(self):
        code = """<?php
class MyClass {
    public function hello() {
        return "world";
    }
}"""
        chunks = self.extractor.extract(code, "Test.php")
        names = [c.name for c in chunks]
        assert "MyClass" in names
        assert "hello" in names

    def test_extract_method_metadata(self):
        code = """<?php
namespace Vendor\\Module\\Model;

class OrderProcessor {
    public function process() {}
    private function validate() {}
}"""
        chunks = self.extractor.extract(code, "OrderProcessor.php")
        methods = [c for c in chunks if c.chunk_type == "method"]

        process = next(c for c in methods if c.name == "process")
        assert process.visibility == "public"
        assert process.class_name == "OrderProcessor"
        assert process.namespace == "Vendor\\Module\\Model"

        validate = next(c for c in methods if c.name == "validate")
        assert validate.visibility == "private"

    def test_extract_namespace(self):
        code = """<?php
namespace Vendor\\Module\\Model;

class Test {}"""
        chunks = self.extractor.extract(code, "Test.php")
        assert chunks[0].namespace == "Vendor\\Module\\Model"

    def test_extract_use_statements(self):
        code = """<?php
namespace Vendor\\Module;

use Magento\\Sales\\Api\\OrderRepositoryInterface;
use Psr\\Log\\LoggerInterface;

class Service {
    public function run() {}
}"""
        chunks = self.extractor.extract(code, "Service.php")
        # All chunks should have dependencies from use statements
        service_class = next(c for c in chunks if c.name == "Service")
        assert any("OrderRepositoryInterface" in d for d in service_class.dependencies)

    def test_extract_interface(self):
        code = """<?php
namespace Vendor\\Module\\Api;

interface OrderProcessorInterface {
    public function process(int $orderId): bool;
}"""
        chunks = self.extractor.extract(code, "OrderProcessorInterface.php")
        iface = next(c for c in chunks if c.name == "OrderProcessorInterface")
        assert iface.chunk_type == "interface"

    def test_extract_class_signature(self):
        """Class chunk should contain signature without method bodies."""
        code = """<?php
class Calculator {
    private int $result;
    public function add(int $n) { $this->result += $n; }
    public function get() { return $this->result; }
}"""
        chunks = self.extractor.extract(code, "Calculator.php")
        class_chunk = next(c for c in chunks if c.chunk_type == "class")
        # Signature should have { ... } for methods, not full bodies
        assert "{ ... }" in class_chunk.content
        assert "$this->result += $n" not in class_chunk.content

    def test_empty_file(self):
        code = "<?php\n"
        chunks = self.extractor.extract(code, "empty.php")
        assert chunks == []

    def test_registration_file(self):
        """registration.php has no classes — should return empty."""
        code = """<?php
\\Magento\\Framework\\Component\\ComponentRegistrar::register(
    \\Magento\\Framework\\Component\\ComponentRegistrar::MODULE,
    'Vendor_Module',
    __DIR__
);"""
        chunks = self.extractor.extract(code, "registration.php")
        assert chunks == []

    def test_line_numbers(self):
        code = """<?php
class MyClass {
    public function first() {
        return 1;
    }

    public function second() {
        return 2;
    }
}"""
        chunks = self.extractor.extract(code, "Test.php")
        first = next(c for c in chunks if c.name == "first")
        second = next(c for c in chunks if c.name == "second")
        assert first.start_line < second.start_line
        assert first.end_line < second.start_line
