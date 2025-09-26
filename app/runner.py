# app/runner.py
from typing import Any, Dict, List, Optional
from app.orchestrator.graph import build_app

def run_command(
    session_id: str,
    user_text: str,
    pointers: Optional[Dict[str, str]] = None,
    ui_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    app = build_app()
    state_out = app.invoke({
        "session_id": session_id,
        "user_text": user_text,
        "pointers": pointers or {},
        "ui_events": ui_events or [],
    })
    return {
        "mode": state_out.get("mode"),
        "plan": state_out.get("plan"),
        "results": state_out.get("results"),
    }
