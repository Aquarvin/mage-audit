-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for storing code chunks with their embeddings
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    repo_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    chunk_type TEXT NOT NULL, -- 'function', 'class', 'method', 'file'
    chunk_name TEXT NOT NULL, -- e.g. 'processOrder', 'OrderProcessor'
    content TEXT NOT NULL, -- actual code
    embedding vector (384), -- BGE-small dimensions
    metadata JSONB DEFAULT '{}', -- extra info (line numbers, dependencies, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx ON code_chunks USING hnsw (embedding vector_cosine_ops);

-- Index for filtering by repo
CREATE INDEX IF NOT EXISTS code_chunks_repo_idx ON code_chunks (repo_name);

-- Index for filtering by file
CREATE INDEX IF NOT EXISTS code_chunks_file_idx ON code_chunks (file_path);