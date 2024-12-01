-- Main Key-Value table
CREATE TABLE IF NOT EXISTS acro_kvs (
    rowid INTEGER PRIMARY KEY,
    key TEXT NOT NULL,
    val TEXT NOT NULL,
    UNIQUE(key, val COLLATE NOCASE) -- Ensures case-insensitive uniqueness
) STRICT;

-- Index for efficient key-based lookups
CREATE INDEX IF NOT EXISTS idx_kvs_by_key ON acro_kvs(key);

-- FTS table with lowercase data
CREATE VIRTUAL TABLE IF NOT EXISTS acro_kvs_fts USING fts5(
    key,
    val,
    tokenize='trigram trigram case_sensitive 0' -- Enables trigram tokenization for partial matching
);


-- The trigger is necessary because we need to keep the key-val in lowercase in the FTS table.
-- Otherwise, we could just use content="acro_kvs" in the FTS table definition and let sqlite
-- handle the syncing of the main and FTS tables.

-- Trigger to populate the FTS table on insert
CREATE TRIGGER IF NOT EXISTS acro_kvs_ai AFTER INSERT ON acro_kvs
BEGIN
    INSERT INTO acro_kvs_fts(rowid, key, val)
    VALUES (new.rowid, lower(new.key), lower(new.val));
END;

-- Trigger to update the FTS table on row updates
CREATE TRIGGER IF NOT EXISTS acro_kvs_au AFTER UPDATE ON acro_kvs
BEGIN
    DELETE FROM acro_kvs_fts WHERE rowid = old.rowid;
    INSERT INTO acro_kvs_fts(rowid, key, val)
    VALUES (new.rowid, lower(new.key), lower(new.val));
END;

-- Trigger to remove entries from the FTS table when rows are deleted
CREATE TRIGGER IF NOT EXISTS acro_kvs_ad AFTER DELETE ON acro_kvs
BEGIN
    DELETE FROM acro_kvs_fts WHERE rowid = old.rowid;
END;
