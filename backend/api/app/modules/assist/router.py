import logging
import uuid
import json

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse

from app.modules.assist.schemas import (
    AssistResponse,
    AssistTurnData,
    AssistResponseData,
    ProviderInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assist", tags=["assist"])

@router.post("/sessions/{session_id}/turns", response_model=AssistResponse)
async def create_assist_turn(
    session_id: str,
    intent_json: str = Form(...),
    trigger_json: str = Form(...),
    client_context_json: str = Form(...),
    image_file: UploadFile = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Handle an Assist turn request (mocked for Phase 1).
    """
    logger.info(f"Received assist turn for session: {session_id}")
    
    try:
        # Validate that the JSON strings can be parsed
        intent_data = json.loads(intent_json)
        trigger_data = json.loads(trigger_json)
        client_context = json.loads(client_context_json)
        
        logger.info(f"Parsed intent: {intent_data}")
        logger.info(f"Parsed trigger: {trigger_data}")
        logger.info(f"Received image: {image_file.filename} ({image_file.content_type})")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse multipart JSON: {e}")
        return JSONResponse(status_code=400, content={"message": "Invalid JSON in form data"})

    # MOCK BEHAVIOR
    turn_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    response_data = AssistResponseData(
        spoken_text="There is a chair directly ahead and a doorway to your left.",
        display_text="Chair ahead. Doorway left.",
        confidence=0.84,
        follow_up_mode="available",
        hazards=[],
        detected_objects=["chair", "doorway"]
    )

    provider_info = ProviderInfo(
        name="mocked_gemini",
        model="mock-1.5-flash",
        latency_ms=1200
    )

    turn_data = AssistTurnData(
        turn_id=turn_id,
        session_id=session_id,
        status="completed",
        response=response_data,
        provider=provider_info
    )

    return AssistResponse(data=turn_data, trace_id=trace_id)
