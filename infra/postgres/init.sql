-- Este script se ejecuta UNA sola vez, la primera vez que se crea el volumen de Postgres.
-- Activa la extensión pgvector, necesaria para guardar "embeddings" (memoria semántica
-- del agente IA) directamente en PostgreSQL, sin necesidad de una base de datos vectorial aparte.

CREATE EXTENSION IF NOT EXISTS vector;
