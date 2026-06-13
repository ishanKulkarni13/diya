from typing import Optional
from pydantic import BaseModel, Field

class AssistResponseData(BaseModel):
    spoken_text: str
    display_text: str
    confidence: Optional[float] = None
    follow_up_mode: Optional[str] = None
    hazards: list[str] = Field(default_factory=list)
    detected_objects: list[str] = Field(default_factory=list)

class ProviderInfo(BaseModel):
    name: str
    model: str
    latency_ms: int

class AssistTurnData(BaseModel):
    turn_id: str
    session_id: str
    status: str
    response: AssistResponseData
    provider: ProviderInfo

class AssistResponse(BaseModel):
    data: AssistTurnData
    trace_id: str
