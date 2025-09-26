# app/models/schemas.py
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

ModeLiteral = Literal["ui_control", "data_query", "agent"]

class PlanArgs(BaseModel):
    # UI
    action: Optional[str] = None
    window: Optional[str] = None

    # Data
    media: Optional[str] = None           # "mp3" | "flac" | ...
    time_window: Optional[str] = None     # "last month", "last 8 months", etc.
    from_folder: Optional[str] = None
    to_disk: Optional[str] = None
    operation: Optional[str] = None       # "moved", "copied", etc.

    # Entities resolved by the agent (e.g., band names)
    entity: Optional[str] = None

class Plan(BaseModel):
    mode: ModeLiteral = Field(..., description="Which subagent to use.")
    args: PlanArgs
