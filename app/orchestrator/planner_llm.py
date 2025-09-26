# app/orchestrator/planner_llm.py
from __future__ import annotations
import json
from typing import Dict, Any, Optional
from app.llm.core import chat_json, extract_json_block
from app.models.schemas import Plan, PlanArgs

SYSTEM_PROMPT = """You are a router for a file-management assistant.
Read the user's sentence and any 'pointers' (concrete IDs like window, folder, disk).
Choose exactly one mode and return a small JSON object:

{
  "mode": "ui_control" | "data_query" | "agent",
  "args": {
    // UI (optional)
    "action": "...",        // e.g. "close_window", "resize_window"
    "window": "...",

    // Data (optional)
    "media": "...",         // e.g. "mp3"
    "time_window": "...",   // e.g. "last month"
    "from_folder": "...",
    "to_disk": "...",
    "operation": "...",     // e.g. "moved", "copied"

    // Entity (optional)
    "entity": "..."         // e.g. "The Beatles"
  }
}

Rules:
- ui_control: if the user asks to manipulate UI (close/focus/resize a window), prefer this mode.
- data_query: if the user asks to list, find, move, or summarize files (by type, time, path, device).
- agent: general questions, interpretation, or research that do not require an immediate UI or data action.
- Use pointers to fill args when present (window, folder, disk). Do not invent IDs.
- If the user's text says "them", "that band", etc., look at the given memory to resolve the entity if present.
- Return JSON only. No explanations.
"""

def _make_user_prompt(user_text: str, pointers: Dict[str, str], memory: Dict[str, Any]) -> str:
    return json.dumps({
        "user_text": user_text,
        "pointers": pointers or {},
        "memory": {k: memory.get(k) for k in ("last_entity", "last_mode", "last_window")}
    }, ensure_ascii=False, indent=2)

def plan_with_llm(user_text: str, pointers: Optional[Dict[str, str]] = None,
                  memory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pointers = pointers or {}
    memory = memory or {}

    raw = chat_json(SYSTEM_PROMPT, _make_user_prompt(user_text, pointers, memory), temperature=0.0)
    jb = extract_json_block(raw)

    try:
        data = json.loads(jb)
        model = Plan(**data)  # validate
        plan_dict = {"mode": model.mode, "args": model.args.model_dump()}
        # Fill window/folder/disk from pointers if model omitted them
        if "window" in pointers and not plan_dict["args"].get("window"):
            plan_dict["args"]["window"] = pointers["window"]
        if "folder" in pointers and not plan_dict["args"].get("from_folder"):
            plan_dict["args"]["from_folder"] = pointers["folder"]
        if "disk" in pointers and not plan_dict["args"].get("to_disk"):
            plan_dict["args"]["to_disk"] = pointers["disk"]
        return plan_dict
    except Exception as e:
        # Safe fallback
        return {"mode": "agent", "args": {"note": "fallback", "error": str(e)}}
