CREATE TABLE IF NOT EXISTS acro (
    rowid INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    val TEXT DEFAULT NULL CHECK (
        val IS NULL OR (
            json_valid(val) AND
            json_type(val) = 'array' AND
            json_array_length(val) > 0
        )
    )
) STRICT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_acro_key ON acro(key);

CREATE VIRTUAL TABLE IF NOT EXISTS fts5_key USING fts5(
    fts_key,
    content='acro',
    content_rowid='rowid'
);

-- Trigger for INSERT
CREATE TRIGGER IF NOT EXISTS acro_ai AFTER INSERT ON acro
BEGIN
    INSERT INTO fts5_key(rowid, fts_key) VALUES (new.rowid, new.key);
END;

-- Trigger for UPDATE
CREATE TRIGGER IF NOT EXISTS acro_au AFTER UPDATE ON acro
BEGIN
    UPDATE fts5_key SET fts_key = new.key WHERE rowid = old.rowid;
END;

-- Trigger for DELETE
CREATE TRIGGER IF NOT EXISTS acro_ad AFTER DELETE ON acro
BEGIN
    DELETE FROM fts5_key WHERE rowid = old.rowid;
END;
