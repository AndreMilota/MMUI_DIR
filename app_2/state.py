# app_2/state.py
"""
State and Pydantic models for the branching LangGraph workflow.

This module defines:
- ActionType enum for routing decisions
- ExecutionPlan Pydantic model for structured LLM output
- GraphState TypedDict for data flowing through the graph
"""
from enum import Enum
from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Classification of user intent for routing."""
    QUERY_RESPOND = "query_respond"          # Query DB, synthesize single result to natural language
    QUERY_DISPLAY = "query_display"          # Query DB, display table to user
    QUERY_STORE = "query_store"              # Query DB, store table for multi-turn dialog
    QUERY_TRANSFORM = "query_transform"      # Query DB, generate source/dest for move/rename/delete
    QUERY_COPY = "query_copy"                # Query DB, generate source/dest for copy
    QUERY_FEED_LLM = "query_feed_llm"        # Query DB, feed results to LLM for AI processing
    QUERY_EXTERNAL = "query_external"        # Query DB, call external app per row
    WEB_SEARCH = "web_search"                # Perform web research
    DIRECT_ANSWER = "direct_answer"          # Respond directly without DB query


class ExecutionPlan(BaseModel):
    """Structured output from the classification LLM call."""

    action_type: ActionType = Field(
        description="Category of action determining which processing branch to use"
    )

    sql: Optional[str] = Field(
        None,
        description="SQL query if action requires database access. Must be valid SQLite."
    )

    processing_instruction: str = Field(
        default="process",
        description="What to do with results: synthesize_to_text, display_table, "
                    "store_for_dialog, delete_files, move_files, rename_files, "
                    "copy_files, feed_to_llm, call_external_app, web_lookup, respond_directly"
    )

    response_text: Optional[str] = Field(
        None,
        description="For direct_answer action type, the complete response text to return"
    )

    llm_instruction: Optional[str] = Field(
        None,
        description="For query_feed_llm, instructions for the LLM processing the table rows"
    )

    external_app: Optional[str] = Field(
        None,
        description="For query_external, name/command of external application to invoke"
    )

    reasoning: str = Field(
        description="Brief explanation of why this action type and approach was chosen"
    )


class GraphState(TypedDict, total=False):
    """State flowing through the LangGraph workflow."""

    # Input
    user_input: str                              # Natural language query from user

    # Time context (for relative-time queries)
    now_ns: Optional[int]                        # Current time as nanoseconds since Unix epoch
    now_iso: Optional[str]                       # Current time as ISO-8601 string

    # Database
    db_path: Optional[str]                       # Path to SQLite database

    # Classification output
    execution_plan: Optional[ExecutionPlan]      # Structured plan from classifier

    # Query execution
    sql: Optional[str]                           # SQL query (copied from plan for convenience)
    query_result: Optional[List[Dict[str, Any]]] # Rows returned from database
    query_error: Optional[str]                   # Error message if query fails

    # Multi-turn storage
    stored_table: Optional[List[Dict[str, Any]]] # Table stored for follow-up queries
    stored_table_description: Optional[str]      # Description of what's in stored_table

    # Final output
    final_response: Optional[str]                # Natural language response to user