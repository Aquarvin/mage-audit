<?php
namespace Vendor\Module\Model;

use Magento\Framework\Model\AbstractModel;

class OrderProcessor extends AbstractModel
{
    protected $orderRepository;
    protected $logger;
    
    public function __construct(
        $orderRepository,
        $logger
    ) {
        $this->orderRepository = $orderRepository;
        $this->logger = $logger;
    }

    public function processOrder($orderId)
    {
        $order = $this->orderRepository->get($orderId);
        
        if ($order->getStatus() == 'pending') {
            $order->setStatus('processing');
            $items = $order->getItems();
            
            foreach ($items as $item) {
                $price = $item->getPrice();
                $qty = $item->getQty();
                $total = $price * $qty;
                $item->setRowTotal($total);
                
                if ($total > 1000) {
                    $discount = $total * 0.1;
                    $item->setDiscount($discount);
                    $item->setRowTotal($total - $discount);
                }
                
                $this->updateInventory($item->getSku(), $qty);
            }
            
            $this->orderRepository->save($order);
            echo "Order processed: " . $orderId;
        }
        
        return true;
    }
    
    private function updateInventory($sku, $qty)
    {
        // Direct SQL query - bad practice
        $connection = $this->getResource()->getConnection();
        $connection->query(
            "UPDATE cataloginventory_stock_item SET qty = qty - $qty WHERE sku = '$sku'"
        );
    }
}