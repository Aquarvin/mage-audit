<?php
namespace Vendor\OrderManager\Observer;

use Magento\Framework\Event\Observer;
use Magento\Framework\Event\ObserverInterface;
use Vendor\OrderManager\Api\OrderProcessorInterface;
use Psr\Log\LoggerInterface;

class OrderPlaceAfter implements ObserverInterface
{
    private OrderProcessorInterface $orderProcessor;
    private LoggerInterface $logger;

    public function __construct(
        OrderProcessorInterface $orderProcessor,
        LoggerInterface $logger
    ) {
        $this->orderProcessor = $orderProcessor;
        $this->logger = $logger;
    }

    public function execute(Observer $observer): void
    {
        $order = $observer->getEvent()->getOrder();
        if ($order === null) {
            $this->logger->warning('OrderPlaceAfter: order is null');
            return;
        }

        $this->logger->info('Processing order after placement', ['order_id' => $order->getEntityId()]);
        $this->orderProcessor->processOrder((int) $order->getEntityId());
    }
}