<?php
namespace Vendor\OrderManager\Plugin;

use Magento\Sales\Api\Data\OrderInterface;
use Magento\Sales\Api\OrderRepositoryInterface;
use Magento\Sales\Model\Order;
use Psr\Log\LoggerInterface;

class OrderSavePlugin
{
    private LoggerInterface $logger;

    public function __construct(LoggerInterface $logger)
    {
        $this->logger = $logger;
    }

    public function afterSave(
        OrderRepositoryInterface $subject,
        OrderInterface $result
    ): OrderInterface {
        if ($result->getState() === Order::STATE_COMPLETE) {
            $this->logger->info(
                'Order completed',
                ['order_id' => $result->getEntityId(), 'total' => $result->getGrandTotal()]
            );
        }
        return $result;
    }
}