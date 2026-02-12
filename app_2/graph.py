# app_2/graph.py
"""
LangGraph workflow with branching for the file management system.

Flow:
1. classify_and_plan: Determine intent and generate execution plan
2. Route to appropriate branch based on action_type
3. Execute SQL (if needed)
4. Process results in branch-specific node
"""
from langgraph.graph import StateGraph, END

from app_2.state import GraphState, ActionType
from app_2.nodes import (
    classify_and_plan,
    execute_sql,
    query_and_respond,
    query_and_display,
    query_and_store,
    query_and_transform,
    query_and_copy,
    query_feed_llm,
    query_external,
    web_search_handler,
    direct_answer_handler,
)


def route_after_classification(state: GraphState) -> str:
    """
    Conditional routing based on the execution plan's action_type.

    Returns the name of the next node to execute.
    """
    plan = state.get("execution_plan")

    if plan is None:
        return "direct_answer"

    action_type = plan.action_type

    # Routes that need SQL execution first
    if action_type == ActionType.QUERY_RESPOND:
        return "execute_sql_respond"
    elif action_type == ActionType.QUERY_DISPLAY:
        return "execute_sql_display"
    elif action_type == ActionType.QUERY_STORE:
        return "execute_sql_store"
    elif action_type == ActionType.QUERY_TRANSFORM:
        return "execute_sql_transform"
    elif action_type == ActionType.QUERY_COPY:
        return "execute_sql_copy"
    elif action_type == ActionType.QUERY_FEED_LLM:
        return "execute_sql_feed_llm"
    elif action_type == ActionType.QUERY_EXTERNAL:
        return "execute_sql_external"

    # Routes that don't need SQL
    elif action_type == ActionType.WEB_SEARCH:
        return "web_search"
    elif action_type == ActionType.DIRECT_ANSWER:
        return "direct_answer"

    # Fallback
    return "direct_answer"


def build_app():
    """Build and compile the branching LangGraph workflow."""
    graph = StateGraph(GraphState)

    # Add the classification node (entry point)
    graph.add_node("classify", classify_and_plan)

    # Add SQL execution nodes (one per branch that needs DB access)
    # We use the same execute_sql function but route to different processing nodes
    graph.add_node("execute_sql_respond", execute_sql)
    graph.add_node("execute_sql_display", execute_sql)
    graph.add_node("execute_sql_store", execute_sql)
    graph.add_node("execute_sql_transform", execute_sql)
    graph.add_node("execute_sql_copy", execute_sql)
    graph.add_node("execute_sql_feed_llm", execute_sql)
    graph.add_node("execute_sql_external", execute_sql)

    # Add processing nodes
    graph.add_node("query_respond", query_and_respond)
    graph.add_node("query_display", query_and_display)
    graph.add_node("query_store", query_and_store)
    graph.add_node("query_transform", query_and_transform)
    graph.add_node("query_copy", query_and_copy)
    graph.add_node("query_feed_llm", query_feed_llm)
    graph.add_node("query_external", query_external)
    graph.add_node("web_search", web_search_handler)
    graph.add_node("direct_answer", direct_answer_handler)

    # Set entry point
    graph.set_entry_point("classify")

    # Add conditional routing after classification
    graph.add_conditional_edges(
        "classify",
        route_after_classification,
        {
            "execute_sql_respond": "execute_sql_respond",
            "execute_sql_display": "execute_sql_display",
            "execute_sql_store": "execute_sql_store",
            "execute_sql_transform": "execute_sql_transform",
            "execute_sql_copy": "execute_sql_copy",
            "execute_sql_feed_llm": "execute_sql_feed_llm",
            "execute_sql_external": "execute_sql_external",
            "web_search": "web_search",
            "direct_answer": "direct_answer",
        }
    )

    # Connect SQL execution nodes to their processing nodes
    graph.add_edge("execute_sql_respond", "query_respond")
    graph.add_edge("execute_sql_display", "query_display")
    graph.add_edge("execute_sql_store", "query_store")
    graph.add_edge("execute_sql_transform", "query_transform")
    graph.add_edge("execute_sql_copy", "query_copy")
    graph.add_edge("execute_sql_feed_llm", "query_feed_llm")
    graph.add_edge("execute_sql_external", "query_external")

    # All processing nodes go to END
    graph.add_edge("query_respond", END)
    graph.add_edge("query_display", END)
    graph.add_edge("query_store", END)
    graph.add_edge("query_transform", END)
    graph.add_edge("query_copy", END)
    graph.add_edge("query_feed_llm", END)
    graph.add_edge("query_external", END)
    graph.add_edge("web_search", END)
    graph.add_edge("direct_answer", END)

    return graph.compile()