# app_2 — Branching LangGraph Workflow

This diagram shows the branching workflow in `app_2/` that classifies user intent and routes to specialized processing nodes.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
    __start__([__start__]):::first
    classify[classify_and_plan<br/><i>LLM: determine intent + generate SQL</i>]

    subgraph SQL_Execution[SQL Execution Nodes]
        exec_respond[execute_sql_respond]
        exec_display[execute_sql_display]
        exec_store[execute_sql_store]
        exec_transform[execute_sql_transform]
        exec_copy[execute_sql_copy]
        exec_feed_llm[execute_sql_feed_llm]
        exec_external[execute_sql_external]
    end

    subgraph Processing[Processing Nodes]
        query_respond[query_and_respond<br/><i>Synthesize to NL</i>]
        query_display[query_and_display<br/><i>Show table</i>]
        query_store[query_and_store<br/><i>Store for multi-turn</i>]
        query_transform[query_and_transform<br/><i>Move/rename/delete</i>]
        query_copy[query_and_copy<br/><i>Copy files</i>]
        query_feed_llm[query_feed_llm<br/><i>AI processing</i>]
        query_external[query_external<br/><i>External app</i>]
    end

    web_search[web_search_handler<br/><i>Web research</i>]
    direct_answer[direct_answer_handler<br/><i>Conversational</i>]

    __end__([__end__]):::last

    __start__ --> classify

    classify -.->|query_respond| exec_respond
    classify -.->|query_display| exec_display
    classify -.->|query_store| exec_store
    classify -.->|query_transform| exec_transform
    classify -.->|query_copy| exec_copy
    classify -.->|query_feed_llm| exec_feed_llm
    classify -.->|query_external| exec_external
    classify -.->|web_search| web_search
    classify -.->|direct_answer| direct_answer

    exec_respond --> query_respond
    exec_display --> query_display
    exec_store --> query_store
    exec_transform --> query_transform
    exec_copy --> query_copy
    exec_feed_llm --> query_feed_llm
    exec_external --> query_external

    query_respond --> __end__
    query_display --> __end__
    query_store --> __end__
    query_transform --> __end__
    query_copy --> __end__
    query_feed_llm --> __end__
    query_external --> __end__
    web_search --> __end__
    direct_answer --> __end__

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```

## Action Types

| Action Type | Description | Requires SQL |
|-------------|-------------|--------------|
| `query_respond` | Return single value as natural language | Yes |
| `query_display` | Display table of files to user | Yes |
| `query_store` | Store table for multi-turn dialog | Yes |
| `query_transform` | Move, rename, or delete files | Yes (source_path, dest_path) |
| `query_copy` | Copy files | Yes (source_path, dest_path) |
| `query_feed_llm` | Feed results to LLM for AI processing | Yes |
| `query_external` | Run external application per row | Yes |
| `web_search` | Perform web research | No |
| `direct_answer` | Respond directly (greetings, chat) | No |

## Example Queries by Action Type

### query_respond
- "How many MP3 files do I have?"
- "Do I have any files older than a month?"
- "How many minutes of Beatles music do I have?"

### query_display
- "Show me all files in C:/Music/Beatles" → filename column only (single pinned directory)
- "List all Beatles songs in C:/Music/Beatles" → filename only, even though filter is on tag_artist
- "List all text files I have" → path + filename columns (no directory pinned, scans everywhere)
- "Show MP3s in C:/Music and its subfolders" → path + filename columns (recursive)
- Timestamps are shown human-readable by default (e.g. `2026-01-10 12:00:00`)

### query_store
- "Remember the MP3 files in my Beatles folder"

### query_transform
- "Delete all .tmp files in C:/Downloads/Temp"
- "Move all files from C:/Downloads to C:/Archive"
- "Rename all files in C:/Projects/Archive by removing the 'archive_' prefix"

### query_copy
- "Copy all jpg files from C:/Pictures to C:/Backup"
- "Update C:/Photos/Backup so it has all the files from C:/Photos/Camera — only copy files not already there" (sync copy using NOT EXISTS)

### query_feed_llm
- "Use AI to suggest better names for my vacation photos"
- "Remove the numeric prefix from all tracks in C:/Music/Playlist" (variable-length prefix — SQL can't do this)

### query_external
- "Run ffmpeg to convert all MP3 files to WAV"

### web_search
- "What is the current price of the Beatles vinyl on Amazon?"

### direct_answer
- "Hello, how are you?"
- "What can you help me with?"
- "What time is it?"