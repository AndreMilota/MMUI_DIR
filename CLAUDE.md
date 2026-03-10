# Claude Code Project Conventions

This file documents coding conventions and patterns for this project that Claude Code should follow in future sessions.

## Marker Comments for Important Operations

When writing code that performs significant operations, add a marker comment to make these locations easy to find:

```python
# <------- LLM CALL: description
response = chat(system_prompt, user_prompt, temperature=0.3)  # <------- LLM CALL: synthesize response

# <------- DATABASE QUERY
cursor.execute(sql)  # <------- DATABASE QUERY
```

### When to use markers:
- **LLM calls**: Any call to `chat()`, `chat_json()`, or similar LLM functions
- **Database queries**: Any `cursor.execute()`, `conn.execute()`, or similar DB operations
- **File system operations**: Actual file moves, copies, deletes
- **External API calls**: HTTP requests, external service calls
- **Other critical operations**: Anything that is the "main action" in a function

### Marker format:
```
# <------- CATEGORY: brief description
```

Categories:
- `LLM CALL` - Large language model invocation
- `DATABASE QUERY` - SQL execution
- `FILE OPERATION` - File system changes
- `EXTERNAL CALL` - External service/API calls

## Modular Prompt Components

When adding guidance to LLM prompts that is specific to certain scenarios:

1. Create the guidance as a module-level variable (e.g., `SQL_ESCALATION_GUIDANCE`)
2. Add detailed comments explaining:
   - Why it's modularized
   - When it should be conditionally included
   - Future optimization possibilities
3. Inject it into prompts using f-string interpolation: `{GUIDANCE_VARIABLE}`

This allows:
- A/B testing different prompt versions
- Conditional inclusion based on query classification
- Model-specific tuning
- Dynamic updates without code changes

## Accessibility

The `print_copy()` function from `app.utils.clipboard` should be used for:
- User requests (input)
- System responses (output)

This copies text to the clipboard for screen readers / speech synthesizers.

Regular `print()` is fine for debug/trace information.

## Virtual File System Testing

When implementing file operations:
- Always use the MockFiles virtual filesystem for testing
- Add explicit checks to ensure real filesystem is not used in test mode
- Add comments noting where PathGuard should be integrated before production use
