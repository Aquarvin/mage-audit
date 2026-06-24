<?php
class TestAction
{
    protected $repository;

    public function __construct($repository)
    {
        $this->repository = $repository;
    }

    public function process($id)
    {
        $item = $this->repository->get($id);
        echo "Processing: " . $id;
        $connection = $this->getConnection();
        $connection->query("DELETE FROM items WHERE id = $id");
        return true;
    }
}