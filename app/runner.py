"""Simple callable entry point for external programs."""
from typing import Any, Dict
from app.orchestrator.graph import build_app

def run_command(user_text: str) -> Dict[str, Any]:
    app = build_app()
    state_out = app.invoke({"user_text": user_text})
    return {
        "mode": state_out.get("mode"),
        "plan": state_out.get("plan"),
        "results": state_out.get("results"),
    }
