"""PHP code extractor using tree-sitter.

Parses PHP files into structured chunks: classes, methods, functions.
Each chunk has metadata: name, type, visibility, line range, dependencies.
"""

from dataclasses import dataclass, field

import tree_sitter_php as tsphp
from tree_sitter import Language, Node, Parser

PHP_LANGUAGE = Language(tsphp.language_php_only())


@dataclass
class CodeChunk:
    """A structured piece of code extracted from a PHP file."""

    name: str
    chunk_type: str  # 'class', 'method', 'function', 'interface', 'trait'
    content: str
    file_path: str
    start_line: int
    end_line: int
    visibility: str | None = None  # 'public', 'protected', 'private'
    class_name: str | None = None  # parent class for methods
    namespace: str | None = None
    dependencies: list[str] = field(default_factory=list)  # use statements


class PHPExtractor:
    """Extracts structured code chunks from PHP source files."""

    def __init__(self) -> None:
        self._parser = Parser(PHP_LANGUAGE)

    def extract(self, code: str, file_path: str = "") -> list[CodeChunk]:
        """Parse PHP code and extract all chunks.

        Args:
            code: PHP source code as string.
            file_path: File path for metadata.

        Returns:
            List of CodeChunk objects.
        """
        tree = self._parser.parse(code.encode("utf-8"))
        root = tree.root_node
        code_bytes = code.encode("utf-8")

        namespace = self._extract_namespace(root, code_bytes)
        dependencies = self._extract_use_statements(root, code_bytes)

        chunks = []

        # Extract classes/interfaces/traits
        for class_node in self._find_nodes(root, "class_declaration"):
            class_chunks = self._extract_class(
                class_node, code_bytes, file_path, namespace, dependencies
            )
            chunks.extend(class_chunks)

        for iface_node in self._find_nodes(root, "interface_declaration"):
            class_chunks = self._extract_class(
                iface_node, code_bytes, file_path, namespace, dependencies
            )
            chunks.extend(class_chunks)

        for trait_node in self._find_nodes(root, "trait_declaration"):
            class_chunks = self._extract_class(
                trait_node, code_bytes, file_path, namespace, dependencies
            )
            chunks.extend(class_chunks)

        # Extract standalone functions (not inside a class)
        for func_node in self._find_nodes(root, "function_definition"):
            # Only top-level functions (parent is program)
            if func_node.parent and func_node.parent.type == "program":
                chunk = self._extract_function(
                    func_node, code_bytes, file_path, namespace, dependencies
                )
                if chunk:
                    chunks.append(chunk)

        return chunks

    def _extract_class(
        self,
        class_node: Node,
        code_bytes: bytes,
        file_path: str,
        namespace: str | None,
        dependencies: list[str],
    ) -> list[CodeChunk]:
        """Extract a class and all its methods as separate chunks."""
        chunks = []

        name_node = class_node.child_by_field_name("name")
        if not name_node:
            return chunks

        class_name = self._node_text(name_node, code_bytes)
        class_type = class_node.type.replace(
            "_declaration", ""
        )  # 'class', 'interface', 'trait'

        # Add the class itself as a chunk
        # (declaration + properties, without method bodies)
        class_content = self._extract_class_signature(class_node, code_bytes)
        chunks.append(
            CodeChunk(
                name=class_name,
                chunk_type=class_type,
                content=class_content,
                file_path=file_path,
                start_line=class_node.start_point[0] + 1,
                end_line=class_node.end_point[0] + 1,
                namespace=namespace,
                dependencies=list(dependencies),
            )
        )

        # Extract each method as a separate chunk
        for method_node in self._find_nodes(class_node, "method_declaration"):
            chunk = self._extract_method(
                method_node, code_bytes, file_path, class_name, namespace, dependencies
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _extract_class_signature(self, class_node: Node, code_bytes: bytes) -> str:
        """Extract class declaration without method bodies.

        Includes: class name, extends, implements, properties, constants.
        Excludes: method bodies (they are separate chunks).
        """
        lines = []
        for child in class_node.children:
            if child.type == "declaration_list":
                lines.append("{")
                for member in child.children:
                    if member.type in ("property_declaration", "const_declaration"):
                        lines.append("    " + self._node_text(member, code_bytes))
                    elif member.type == "method_declaration":
                        # Only signature, not body
                        sig = self._extract_method_signature(member, code_bytes)
                        lines.append("    " + sig)
                lines.append("}")
            else:
                lines.append(self._node_text(child, code_bytes))
        return "\n".join(lines)

    def _extract_method_signature(self, method_node: Node, code_bytes: bytes) -> str:
        """Extract method signature without body."""
        parts = []
        for child in method_node.children:
            if child.type == "compound_statement":
                break  # stop before body
            parts.append(self._node_text(child, code_bytes))
        return " ".join(parts) + " { ... }"

    def _extract_method(
        self,
        method_node: Node,
        code_bytes: bytes,
        file_path: str,
        class_name: str,
        namespace: str | None,
        dependencies: list[str],
    ) -> CodeChunk | None:
        """Extract a single method as a chunk."""
        name_node = method_node.child_by_field_name("name")
        if not name_node:
            return None

        name = self._node_text(name_node, code_bytes)
        visibility = self._extract_visibility(method_node, code_bytes)

        return CodeChunk(
            name=name,
            chunk_type="method",
            content=self._node_text(method_node, code_bytes),
            file_path=file_path,
            start_line=method_node.start_point[0] + 1,
            end_line=method_node.end_point[0] + 1,
            visibility=visibility,
            class_name=class_name,
            namespace=namespace,
            dependencies=list(dependencies),
        )

    def _extract_function(
        self,
        func_node: Node,
        code_bytes: bytes,
        file_path: str,
        namespace: str | None,
        dependencies: list[str],
    ) -> CodeChunk | None:
        """Extract a standalone function as a chunk."""
        name_node = func_node.child_by_field_name("name")
        if not name_node:
            return None

        return CodeChunk(
            name=self._node_text(name_node, code_bytes),
            chunk_type="function",
            content=self._node_text(func_node, code_bytes),
            file_path=file_path,
            start_line=func_node.start_point[0] + 1,
            end_line=func_node.end_point[0] + 1,
            namespace=namespace,
            dependencies=list(dependencies),
        )

    def _extract_visibility(self, node: Node, code_bytes: bytes) -> str | None:
        """Extract visibility modifier from a method/property."""
        for child in node.children:
            if child.type == "visibility_modifier":
                return self._node_text(child, code_bytes)
        return None

    def _extract_namespace(self, root: Node, code_bytes: bytes) -> str | None:
        """Extract namespace from the file."""
        for node in self._find_nodes(root, "namespace_definition"):
            name_node = node.child_by_field_name("name")
            if name_node:
                return self._node_text(name_node, code_bytes)
            # Try namespace_name child
            for child in node.children:
                if child.type == "namespace_name":
                    return self._node_text(child, code_bytes)
        return None

    def _extract_use_statements(self, root: Node, code_bytes: bytes) -> list[str]:
        """Extract all use (import) statements."""
        uses = []
        for node in self._find_nodes(root, "namespace_use_declaration"):
            for child in node.children:
                if child.type == "namespace_use_clause":
                    for inner in child.children:
                        if inner.type == "qualified_name":
                            uses.append(self._node_text(inner, code_bytes))
        return uses

    def _find_nodes(self, node: Node, type_name: str) -> list[Node]:
        """Recursively find all nodes of a given type."""
        results = []
        if node.type == type_name:
            results.append(node)
        for child in node.children:
            results.extend(self._find_nodes(child, type_name))
        return results

    def _node_text(self, node: Node, code_bytes: bytes) -> str:
        """Get text content of a node."""
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8")
