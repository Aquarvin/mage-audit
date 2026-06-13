"""Day 1 Phase 1: Understanding tree-sitter and AST."""

import tree_sitter_php as tsphp
from tree_sitter import Language, Parser

# Initialize PHP parser
PHP_LANGUAGE = Language(tsphp.language_php_only())
parser = Parser(PHP_LANGUAGE)

# Simple PHP code
code = b"""\
<?php
namespace Vendor\\Module\\Model;

use Magento\\Sales\\Api\\OrderRepositoryInterface;
use Psr\\Log\\LoggerInterface;

class OrderProcessor
{
    private OrderRepositoryInterface $orderRepository;
    private LoggerInterface $logger;

    public function __construct(
        OrderRepositoryInterface $orderRepository,
        LoggerInterface $logger
    ) {
        $this->orderRepository = $orderRepository;
        $this->logger = $logger;
    }

    public function processOrder(int $orderId): bool
    {
        $order = $this->orderRepository->get($orderId);
        if ($order->getStatus() === 'pending') {
            $order->setStatus('processing');
            $this->orderRepository->save($order);
            $this->logger->info('Order processed: ' . $orderId);
            return true;
        }
        return false;
    }

    private function calculateDiscount(float $total): float
    {
        if ($total > 1000) {
            return $total * 0.1;
        }
        return 0.0;
    }
}
"""

# Parse
tree = parser.parse(code)
root = root = tree.root_node

# --- Experiment 1: What does the AST look like? ---
print("=== Experiment 1: AST structure ===\n")
print(f"Root node type: {root.type}")
print(f"Root children count: {root.child_count}")
print(f"Source code bytes: {len(code)}")
print()


def print_tree(node, indent=0, max_depth=4):
    """Print AST tree up to max_depth."""
    if indent > max_depth:
        return
    # Show node type + text preview for leaf nodes
    text_preview = ""
    if node.child_count == 0:
        text = code[node.start_byte : node.end_byte].decode("utf-8")
        if len(text) < 40:
            text_preview = f'  "{text}"'
    print(
        f"{'  ' * indent}{node.type}"
        f" [{node.start_point[0]}:{node.start_point[1]}"
        f"-{node.end_point[0]}:{node.end_point[1]}]"
        f"{text_preview}"
    )
    for child in node.children:
        print_tree(child, indent + 1, max_depth)


print_tree(root, max_depth=3)

# --- Experiment 2: Find all classes ---
print("\n\n=== Experiment 2: Find all classes ===\n")


def find_nodes(node, type_name):
    """Recursively find all nodes of a given type."""
    results = []
    if node.type == type_name:
        results.append(node)
    for child in node.children:
        results.extend(find_nodes(child, type_name))
    return results


classes = find_nodes(root, "class_declaration")
for cls in classes:
    name_node = cls.child_by_field_name("name")
    name = code[name_node.start_byte : name_node.end_byte].decode("utf-8")
    print(f"Class: {name} (line {cls.start_point[0] + 1})")

# --- Experiment 3: Find all methods ---
print("\n=== Experiment 3: Find all methods ===\n")

methods = find_nodes(root, "method_declaration")
for method in methods:
    name_node = method.child_by_field_name("name")
    name = code[name_node.start_byte : name_node.end_byte].decode("utf-8")

    # Get visibility
    visibility = "unknown"
    for child in method.children:
        if child.type in ("visibility_modifier", "public", "private", "protected"):
            visibility = code[child.start_byte : child.end_byte].decode("utf-8")
            break

    # Get line range
    start_line = method.start_point[0] + 1
    end_line = method.end_point[0] + 1

    # Get full method text
    method_text = code[method.start_byte : method.end_byte].decode("utf-8")

    print(
        f"  {visibility} {name}() — lines {start_line}-{end_line} ({end_line - start_line + 1} lines)"
    )

# --- Experiment 4: Find all use statements (imports) ---
print("\n=== Experiment 4: Find use statements ===\n")

use_declarations = find_nodes(root, "use_declaration")
for use in use_declarations:
    text = code[use.start_byte : use.end_byte].decode("utf-8")
    print(f"  {text}")

# --- Experiment 5: Find namespace ---
print("\n=== Experiment 5: Namespace ===\n")
