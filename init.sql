-- Enable useful PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Trigram similarity (fuzzy name search)
CREATE EXTENSION IF NOT EXISTS "btree_gin";   -- GIN indexes for composite queries
CREATE EXTENSION IF NOT EXISTS "unaccent";    -- Remove accents for search (Álvarez -> Alvarez)

-- Unaccent text search dictionary
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS football_search (COPY = spanish);
ALTER TEXT SEARCH CONFIGURATION football_search
    ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;
