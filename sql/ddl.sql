-- DDL for creating the Acro table as a STRICT table.
--
-- Table Description:
-- - `key`: Primary key column storing unique text values.
-- - `val`: JSON column with strict constraints:
--   - Must be NULL or a valid JSON array.
--   - The array must have at least one element.
--   - All elements in the array must be text strings.
-- - STRICT mode ensures exact type enforcement.

CREATE TABLE IF NOT EXISTS Acro (
    key TEXT PRIMARY KEY, -- Unique identifier for each record
    val TEXT DEFAULT NULL CHECK (
        val IS NULL OR (
            json_valid(val) AND                      -- Ensure the value is valid JSON
            json_type(val) = 'array' AND             -- JSON must be of type 'array'
            json_array_length(val) > 0              -- Array must not be empty
        )
    )
) STRICT;
