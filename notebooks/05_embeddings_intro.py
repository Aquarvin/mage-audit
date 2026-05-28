"""Day 5: Understanding embeddings through experiments."""

import numpy as np
from sentence_transformers import SentenceTransformer


def main():
    # Load a small, fast model — runs on CPU, no GPU needed
    print("Loading model...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    print(f"Model loaded. Embedding dimensions: {model.get_embedding_dimension()}")

    # --- Experiment 1: What does an embedding look like? ---
    print("\n=== Experiment 1: What is an embedding? ===\n")

    text = "Process customer order and update inventory"
    embedding = model.encode(text)

    print(f"Text: '{text}'")
    print(f"Type: {type(embedding)}")
    print(f"Shape: {embedding.shape}")
    print(f"First 10 values: {embedding[:10]}")
    print(f"Min: {embedding.min():.4f}, Max: {embedding.max():.4f}")

    # --- Experiment 2: Similar texts → similar vectors ---
    print("\n=== Experiment 2: Similarity between texts ===\n")

    texts = [
        "Process customer order and update inventory",  # 0: original
        "Handle order processing and stock management",  # 1: similar meaning
        "Update product quantities after purchase",  # 2: related
        "Configure admin panel settings for store",  # 3: different topic
        "SELECT * FROM users WHERE id = 1",  # 4: completely different
    ]

    embeddings = model.encode(texts)
    print(f"Encoded {len(texts)} texts → matrix shape: {embeddings.shape}")

    # Calculate cosine similarity between first text and all others
    # Cosine similarity = dot product of normalized vectors
    from numpy.linalg import norm

    base = embeddings[0]
    print(f"\nSimilarity to: '{texts[0]}'\n")

    for i in range(1, len(texts)):
        cos_sim = np.dot(base, embeddings[i]) / (norm(base) * norm(embeddings[i]))
        print(f"  {cos_sim:.4f}  '{texts[i]}'")

    # --- Experiment 3: Code embeddings ---
    print("\n=== Experiment 3: PHP code embeddings ===\n")

    code_snippets = [
        "public function processOrder($orderId) { $order = $this->orderRepository->get($orderId); }",
        "public function getOrderById($id) { return $this->repository->load($id); }",
        "public function updateInventory($sku, $qty) { $this->stockRegistry->updateStock($sku, $qty); }",
        "public function getProductPrice($productId) { return $this->product->getPrice(); }",
        "public function sendEmail($to, $subject) { $this->transportBuilder->send(); }",
        "public function processPayment($order) { $this->gateway->capture($order->getPayment()); }",
    ]

    code_embeddings = model.encode(code_snippets)

    query = "find functions related to order handling"
    query_embedding = model.encode(query)

    print(f"Query: '{query}'\n")
    print("Results (sorted by similarity):\n")

    similarities = []
    for i, snippet in enumerate(code_snippets):
        cos_sim = np.dot(query_embedding, code_embeddings[i]) / (
            norm(query_embedding) * norm(code_embeddings[i])
        )
        similarities.append((cos_sim, snippet))

    # Sort by similarity, highest first
    similarities.sort(reverse=True)
    for sim, snippet in similarities:
        marker = "✓" if sim > 0.5 else " "
        print(f"  {marker} {sim:.4f}  {snippet[:80]}...")


main()
