# Acrobot

A dead-simple Telegram bot for managing key-value pairs.

## Why

I built this for an internal chat group because I kept forgetting all the random acronyms
flying around. I needed a quick way to store and retrieve them, even if I could only
remember a fragment.

This bot can be added to any Telegram group and invoked with the `/acro` command. It manages
key-value pairs and includes a `search` feature that performs a full-text search across the
database. If I remember even part of a key or value, I can find it in no time.

## Architecture

The backend is a single long-polling Telegram bot backed by a distributed SQLite database on
Turso. Full-text search is powered by SQLite's [FTS5] with the [Trigram] tokenizer and
[BM25] ranking. The app runs on a small 512MB Fly.io instance. You can check the full
database structure in the [DDL] file.

## Usage

Here's a list of all the supported commands:

| **Feature**                                 | **Command**                                          |
| ------------------------------------------- | ---------------------------------------------------- |
| **Add a key with values**                   | - `/acro add <key> <val1> <val2> ...`                |
|                                             | - `/acro add "key with spaces" <val1> <val2> ...`    |
|                                             | - `/acro add <key> "value with spaces"`              |
| **Retrieve values for a key**               | - `/acro get <key>`                                  |
|                                             | - `/acro get "key with spaces"`                      |
| **Remove specific values**                  | - `/acro remove <key> <val1> <val2> ...`             |
|                                             | - `/acro remove "key with spaces" <val1> <val2> ...` |
| **Delete a key**                            | - `/acro delete <key>`                               |
|                                             | - `/acro delete "key with spaces"`                   |
| **List a few random keys**                  | - `/acro list`                                       |
| **Fuzzy search across all keys and values** | - `/acro search <key>`                               |
|                                             | - `/acro search "key with spaces"`                   |
|                                             | - `/acro search <value>`                             |

Here's a GIF showing the bot in action:

https://github.com/user-attachments/assets/7271124b-be35-43b6-9869-8b7afa0a8809

## Deployment

The [CI] is configured to deploy the bot to a 512MB [Fly.io] machine on every push to the
`main` branch.

## Observability

The app streams all log messages to [Pydantic Logfire]. Logs appear as follows:

![Pydantic logfire](https://github.com/user-attachments/assets/7b542bb3-e5f8-4f37-93d7-0b9d992fed94)


[ddl]: ./sql/ddl.sql
[fts5]: https://sqlite.org/fts5.html
[trigram]: https://sqlite.org/fts5.html#the_trigram_tokenizer
[bm25]: https://sqlite.org/fts5.html#the_bm25_function
[telegram bot]: https://core.telegram.org/bots#how-do-i-create-a-bot
[ci]: ./.github/workflows/ci.yml
[fly.io]: https://fly.io/
[pydantic logfire]: https://pydantic.dev/logfire
