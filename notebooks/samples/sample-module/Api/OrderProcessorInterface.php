<?php
namespace Vendor\OrderManager\Api;

interface OrderProcessorInterface
{
    /**
     * Process an order by ID.
     *
     * @param int $orderId
     * @return bool
     */
    public function processOrder(int $orderId): bool;
}