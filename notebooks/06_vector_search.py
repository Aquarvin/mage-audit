"""Day 5: Store PHP code embeddings in pgvector and search."""

import asyncio
import json
import uuid

import asyncpg

from src.core.embeddings import LocalEmbedder

# Sample PHP functions to index (simulating a Magento module)
SAMPLE_FUNCTIONS = [
    {
        "file_path": "Model/OrderProcessor.php",
        "chunk_type": "method",
        "chunk_name": "processOrder",
        "content": """public function processOrder($orderId)
{
    $order = $this->orderRepository->get($orderId);
    if ($order->getStatus() == 'pending') {
        $order->setStatus('processing');
        $this->orderRepository->save($order);
    }
    return true;
}""",
    },
    {
        "file_path": "Model/OrderProcessor.php",
        "chunk_type": "method",
        "chunk_name": "updateInventory",
        "content": """private function updateInventory($sku, $qty)
{
    $connection = $this->getResource()->getConnection();
    $connection->query(
        "UPDATE cataloginventory_stock_item SET qty = qty - $qty WHERE sku = '$sku'"
    );
}""",
    },
    {
        "file_path": "Model/PaymentHandler.php",
        "chunk_type": "method",
        "chunk_name": "capturePayment",
        "content": """public function capturePayment(OrderInterface $order)
{
    $payment = $order->getPayment();
    $this->gateway->capture($payment);
    $this->logger->info('Payment captured for order ' . $order->getIncrementId());
}""",
    },
    {
        "file_path": "Observer/OrderPlaceAfter.php",
        "chunk_type": "method",
        "chunk_name": "execute",
        "content": """public function execute(Observer $observer)
{
    $order = $observer->getEvent()->getOrder();
    $this->emailSender->sendOrderConfirmation($order);
    $this->inventoryManager->reserveItems($order->getItems());
}""",
    },
    {
        "file_path": "Plugin/OrderSavePlugin.php",
        "chunk_type": "method",
        "chunk_name": "afterSave",
        "content": """public function afterSave(OrderRepositoryInterface $subject, OrderInterface $order)
{
    if ($order->getState() === Order::STATE_COMPLETE) {
        $this->rewardPoints->addPoints($order->getCustomerId(), $order->getGrandTotal());
    }
    return $order;
}""",
    },
    {
        "file_path": "Model/ProductExporter.php",
        "chunk_type": "method",
        "chunk_name": "exportToCsv",
        "content": """public function exportToCsv(array $productIds): string
{
    $products = $this->productRepository->getList($this->buildSearchCriteria($productIds));
    $csv = $this->csvWriter->open('products_export.csv');
    foreach ($products->getItems() as $product) {
        $csv->writeLine([$product->getSku(), $product->getName(), $product->getPrice()]);
    }
    return $csv->getPath();
}""",
    },
    {
        "file_path": "Model/CustomerNotifier.php",
        "chunk_type": "method",
        "chunk_name": "notifyLowStock",
        "content": """public function notifyLowStock(string $sku, int $currentQty)
{
    if ($currentQty < $this->configProvider->getLowStockThreshold()) {
        $this->emailSender->sendLowStockAlert($sku, $currentQty);
        $this->logger->warning('Low stock alert', ['sku' => $sku, 'qty' => $currentQty]);
    }
}""",
    },
    {
        "file_path": "Controller/Adminhtml/Order/Process.php",
        "chunk_type": "method",
        "chunk_name": "execute",
        "content": """public function execute()
{
    $orderId = $this->getRequest()->getParam('order_id');
    try {
        $this->orderProcessor->processOrder((int) $orderId);
        $this->messageManager->addSuccessMessage(__('Order processed successfully.'));
    } catch (\\Exception $e) {
        $this->messageManager->addErrorMessage($e->getMessage());
    }
    return $this->resultRedirectFactory->create()->setPath('sales/order/view', ['order_id' => $orderId]);
}""",
    },
]


async def main():
    # Initialize embedder
    print("Loading embedding model...")
    embedder = LocalEmbedder()
    print(f"Model: {embedder.model}, dimensions: {embedder.dimensions}")

    # Connect to database
    # asyncpg uses a different URL format than SQLAlchemy
    conn = await asyncpg.connect(
        host="localhost",
        port=5433,
        user="mageaudit",
        password="dev_password",
        database="mage_audit",
    )

    # Clear old data (for reruns)
    await conn.execute(
        "DELETE FROM code_chunks WHERE repo_name = 'test-magento-module'"
    )

    # --- Step 1: Generate embeddings and store ---
    print(f"\n=== Indexing {len(SAMPLE_FUNCTIONS)} code chunks ===\n")

    texts_to_embed = [func["content"] for func in SAMPLE_FUNCTIONS]
    result = embedder.embed(texts_to_embed)

    for i, func in enumerate(SAMPLE_FUNCTIONS):
        vector_str = "[" + ",".join(str(v) for v in result.vectors[i]) + "]"
        await conn.execute(
            """
            INSERT INTO code_chunks (id, repo_name, file_path, chunk_type, chunk_name, content, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8::jsonb)
            """,
            uuid.uuid4(),
            "test-magento-module",
            func["file_path"],
            func["chunk_type"],
            func["chunk_name"],
            func["content"],
            vector_str,
            json.dumps({"indexed_by": "day5_experiment"}),
        )
        print(f"  ✓ Indexed: {func['file_path']}::{func['chunk_name']}")

    count = await conn.fetchval("SELECT COUNT(*) FROM code_chunks")
    print(f"\nTotal chunks in database: {count}")

    # --- Step 2: Semantic search ---
    queries = [
        "order processing logic",
        "payment and billing",
        "inventory stock management",
        "sending emails and notifications",
        "security vulnerability SQL injection",
    ]

    for query in queries:
        print(f"\n{'=' * 60}")
        print(f"  Query: '{query}'")
        print(f"{'=' * 60}\n")

        query_embedding = embedder.embed([query])
        query_vector_str = (
            "[" + ",".join(str(v) for v in query_embedding.vectors[0]) + "]"
        )

        rows = await conn.fetch(
            """
            SELECT
                chunk_name,
                file_path,
                1 - (embedding <=> $1::vector) AS similarity,
                LEFT(content, 80) AS preview
            FROM code_chunks
            WHERE repo_name = 'test-magento-module'
            ORDER BY embedding <=> $1::vector
            LIMIT 3
            """,
            query_vector_str,
        )

        for row in rows:
            marker = "✓" if row["similarity"] > 0.5 else " "
            print(
                f"  {marker} {row['similarity']:.4f}  "
                f"{row['file_path']}::{row['chunk_name']}"
            )
            print(f"           {row['preview']}...")

    await conn.close()
    print("\nDone!")


asyncio.run(main())
