-- Create the main table `acro` with strict mode
CREATE TABLE IF NOT EXISTS acro (
    rowid INTEGER PRIMARY KEY, -- Primary key auto-increments by default
    key TEXT NOT NULL UNIQUE, -- Unique constraint ensures no duplicate keys
    val TEXT DEFAULT NULL CHECK (
        val IS NULL OR (
            json_valid(val) AND
            json_type(val) = 'array' AND
            json_array_length(val) > 0
        )
    )
) STRICT;

-- Create a unique index on the `key` column for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_acro_key ON acro(key);

-- Create the FTS5 table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS acro_fts USING fts5(
    key, -- Column to be searchable
    content=''
);

-- Trigger to handle inserts into `acro`
CREATE TRIGGER IF NOT EXISTS acro_ai AFTER INSERT ON acro
BEGIN
    INSERT INTO acro_fts(rowid, key) VALUES (new.rowid, new.key);
END;

-- Trigger to handle updates to `acro`
CREATE TRIGGER IF NOT EXISTS acro_au AFTER UPDATE ON acro
WHEN old.key != new.key
BEGIN
    UPDATE acro_fts SET key = new.key WHERE rowid = old.rowid;
END;

-- Trigger to handle deletions from `acro`
CREATE TRIGGER IF NOT EXISTS acro_ad AFTER DELETE ON acro
BEGIN
    INSERT INTO acro_fts(acro_fts, rowid, key) VALUES ('delete', old.rowid, old.key);
END;
