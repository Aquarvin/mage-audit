"""Test the PHP extractor on our sample file."""

from pathlib import Path

from src.languages.php import PHPExtractor

# Use our existing bad_module.php
code = Path("notebooks/samples/bad_module.php").read_text(encoding="utf-8")

extractor = PHPExtractor()
chunks = extractor.extract(code, file_path="Model/OrderProcessor.php")

print(f"Total chunks extracted: {len(chunks)}\n")

for chunk in chunks:
    print(f"{'=' * 60}")
    print(f"  Name: {chunk.name}")
    print(f"  Type: {chunk.chunk_type}")
    print(f"  Class: {chunk.class_name or '(top-level)'}")
    print(f"  Visibility: {chunk.visibility or 'N/A'}")
    print(f"  Lines: {chunk.start_line}-{chunk.end_line}")
    print(f"  Namespace: {chunk.namespace}")
    print(f"  Dependencies: {chunk.dependencies}")
    print(f"  Content length: {len(chunk.content)} chars")
    print(f"{'=' * 60}")
    print(chunk.content)
    print()
