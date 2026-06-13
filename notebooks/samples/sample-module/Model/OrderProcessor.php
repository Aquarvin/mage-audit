<?php
namespace Vendor\OrderManager\Model;

use Magento\Sales\Api\OrderRepositoryInterface;
use Magento\Sales\Model\Order;
use Psr\Log\LoggerInterface;
use Vendor\OrderManager\Api\OrderProcessorInterface;

class OrderProcessor implements OrderProcessorInterface
{
    private OrderRepositoryInterface $orderRepository;
    private LoggerInterface $logger;
    private float $discountThreshold;

    public function __construct(
        OrderRepositoryInterface $orderRepository,
        LoggerInterface $logger,
        float $discountThreshold = 1000.0
    ) {
        $this->orderRepository = $orderRepository;
        $this->logger = $logger;
        $this->discountThreshold = $discountThreshold;
    }

    public function processOrder(int $orderId): bool
    {
        try {
            $order = $this->orderRepository->get($orderId);

            if ($order->getState() !== Order::STATE_NEW) {
                $this->logger->info("Order {$orderId} is not new, skipping.");
                return false;
            }

            $order->setState(Order::STATE_PROCESSING);
            $order->setStatus(Order::STATE_PROCESSING);

            foreach ($order->getItems() as $item) {
                $this->applyItemDiscount($item);
            }

            $this->orderRepository->save($order);
            $this->logger->info("Order {$orderId} processed successfully.");
            return true;

        } catch (\Exception $e) {
            $this->logger->error("Failed to process order {$orderId}: " . $e->getMessage());
            return false;
        }
    }

    private function applyItemDiscount($item): void
    {
        $rowTotal = $item->getPrice() * $item->getQtyOrdered();
        if ($rowTotal > $this->discountThreshold) {
            $discount = $rowTotal * 0.1;
            $item->setDiscountAmount($discount);
            $this->logger->debug("Applied discount {$discount} to item {$item->getSku()}");
        }
    }
}