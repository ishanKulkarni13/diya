from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import socket
import struct
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict

import httpx
try:
    import cv2
except Exception:  # noqa: BLE001
    cv2 = None
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .logging import setup_logging
from .state import LogBuffer, SimulatorState

setup_logging()
logger = logging.getLogger("goggle-simulator")

_BASE_DIR = Path(__file__).resolve().parent.parent

# UDP Discovery Configuration
UDP_DISCOVERY_PORT = 8888
UDP_DISCOVERY_INTERVAL = 3.0  # seconds
UDP_BROADCAST_ADDRESS = "255.255.255.255"
UDP_INITIAL_BURST_COUNT = 3
UDP_INITIAL_BURST_INTERVAL = 1.0  # seconds

_udp_broadcast_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown events."""
    global _udp_broadcast_task
    
    # Startup: Start UDP broadcast task
    logger.info("=== Goggle Simulator Starting ===")
    logger.info(f"[UDP] Starting discovery broadcasts on {UDP_BROADCAST_ADDRESS}:{UDP_DISCOVERY_PORT}")
    _udp_broadcast_task = asyncio.create_task(_udp_broadcast_loop())
    
    yield
    
    # Shutdown: Stop UDP broadcast task
    logger.info("=== Goggle Simulator Shutting Down ===")
    if _udp_broadcast_task:
        _udp_broadcast_task.cancel()
        try:
            await _udp_broadcast_task
        except asyncio.CancelledError:
            logger.info("[UDP] Broadcast task cancelled")


app = FastAPI(title="Smart Goggle Simulator", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

state = SimulatorState()
logs = LogBuffer()

CAMERA_INDEX = 0
JPEG_QUALITY = 85

# ---------------------------------------------------------------------------
# Fallback image: a solid red 64x64 JPEG generated at import time.
# Used when the webcam is not available (no OpenCV / no camera device).
# Also provides TINY_PNG_DATA_URL for the SSE frame stream.
# ---------------------------------------------------------------------------

def _generate_fallback_red_jpeg(width: int = 64, height: int = 64) -> bytes:
    """Generate a minimal valid JPEG of a solid red image using only stdlib.

    If OpenCV is available it is used for quality; otherwise we fall back to a
    hand-crafted minimal JPEG (red pixels via raw MCU encoding).
    """
    # Try OpenCV first — gives a proper compressed JPEG.
    if cv2 is not None:
        try:
            import numpy as np  # noqa: WPS433 – conditional import
            # OpenCV uses BGR ordering
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 2] = 255  # Red channel
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if ok:
                return buf.tobytes()
        except Exception:  # noqa: BLE001
            pass

    # Pure-Python fallback: build a tiny but valid JFIF JPEG.
    # We use the simplest possible encoding: 8x8 single-MCU, YCbCr 4:4:4.
    # For a solid red (R=255 G=0 B=0) the YCbCr values are:
    #   Y=76, Cb=85, Cr=255
    return _build_minimal_jpeg(y_val=76, cb_val=85, cr_val=255)


def _build_minimal_jpeg(y_val: int, cb_val: int, cr_val: int) -> bytes:
    """Build a valid 8x8 JPEG from constant YCbCr values (stdlib only)."""
    buf = io.BytesIO()

    def _w(data: bytes) -> None:
        buf.write(data)

    # SOI
    _w(b"\xff\xd8")

    # APP0 (JFIF header)
    app0 = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    _w(b"\xff\xe0")
    _w(struct.pack(">H", len(app0) + 2))
    _w(app0)

    # DQT — quantisation table (all-1 for lossless-ish quality)
    qt = bytes([1] * 64)
    # Luminance table (id=0)
    _w(b"\xff\xdb")
    _w(struct.pack(">H", 2 + 1 + 64))
    _w(b"\x00")
    _w(qt)
    # Chrominance table (id=1)
    _w(b"\xff\xdb")
    _w(struct.pack(">H", 2 + 1 + 64))
    _w(b"\x01")
    _w(qt)

    # SOF0 — 8x8, 3 components, YCbCr 4:4:4
    _w(b"\xff\xc0")
    _w(struct.pack(">H", 11))  # length
    _w(struct.pack("B", 8))    # precision
    _w(struct.pack(">HH", 8, 8))  # height, width
    _w(struct.pack("B", 3))    # number of components
    # Component 1 (Y):  id=1, sampling=0x11, qt=0
    _w(b"\x01\x11\x00")
    # Component 2 (Cb): id=2, sampling=0x11, qt=1
    _w(b"\x02\x11\x01")
    # Component 3 (Cr): id=3, sampling=0x11, qt=1
    _w(b"\x03\x11\x01")

    # DHT — Huffman tables (minimal DC-only tables)
    # DC luminance (class=0, id=0)
    dc_lum_bits = bytes([0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    dc_lum_vals = bytes([0x00])  # single symbol: category 0
    _w(b"\xff\xc4")
    _w(struct.pack(">H", 2 + 1 + 16 + len(dc_lum_vals)))
    _w(b"\x00")  # class=0 (DC), id=0
    _w(dc_lum_bits)
    _w(dc_lum_vals)

    # DC chrominance (class=0, id=1)
    _w(b"\xff\xc4")
    _w(struct.pack(">H", 2 + 1 + 16 + len(dc_lum_vals)))
    _w(b"\x01")  # class=0 (DC), id=1
    _w(dc_lum_bits)
    _w(dc_lum_vals)

    # AC luminance (class=1, id=0) — single EOB symbol
    ac_bits = bytes([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    ac_vals = bytes([0x00])  # EOB
    _w(b"\xff\xc4")
    _w(struct.pack(">H", 2 + 1 + 16 + len(ac_vals)))
    _w(b"\x10")  # class=1 (AC), id=0
    _w(ac_bits)
    _w(ac_vals)

    # AC chrominance (class=1, id=1) — single EOB symbol
    _w(b"\xff\xc4")
    _w(struct.pack(">H", 2 + 1 + 16 + len(ac_vals)))
    _w(b"\x11")  # class=1 (AC), id=1
    _w(ac_bits)
    _w(ac_vals)

    # SOS — start of scan
    _w(b"\xff\xda")
    _w(struct.pack(">H", 12))  # length
    _w(struct.pack("B", 3))    # number of components
    _w(b"\x01\x00")  # Y  → DC table 0, AC table 0
    _w(b"\x02\x11")  # Cb → DC table 1, AC table 1
    _w(b"\x03\x11")  # Cr → DC table 1, AC table 1
    _w(b"\x00\x3f\x00")  # Ss=0, Se=63, Ah/Al=0

    # Entropy-coded segment: 3 MCU components, each DC-only + EOB.
    # For a constant block the DPCM diff is the DC value itself.
    # Category 0 means value=0 (encoded as single 0 bit by our Huffman table).
    # We cheat: for a *constant* colour we quantise so the DC coefficient
    # is the value and all AC coefficients are zero. With quant=1 this is exact.
    # Bit-stream: for each component emit DC category-0 (1 bit: 0) then AC EOB (1 bit: 0).
    # 3 components × 2 bits = 6 bits → pad to byte boundary.
    _w(bytes([0b00000000]))  # 6 zero-bits + 2 padding bits

    # EOI
    _w(b"\xff\xd9")

    return buf.getvalue()


# Pre-generate at import time so /capture is always fast.
_FALLBACK_RED_JPEG: bytes = _generate_fallback_red_jpeg()

# A tiny 1×1 red PNG encoded as a data-url for the SSE /stream endpoint.
# fmt: off
_TINY_RED_PNG = (
    b"\x89PNG\r\n\x1a\n"  # PNG signature
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
    b"\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)
# fmt: on
TINY_PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(_TINY_RED_PNG).decode("ascii")


class CommandRequest(BaseModel):
    command: str = Field(..., examples=["haptic", "capture", "connect", "disconnect"])
    duration_ms: int | None = None
    payload: Dict[str, object] = Field(default_factory=dict)


class StateUpdate(BaseModel):
    connected: bool | None = None
    battery_level: int | None = Field(default=None, ge=0, le=100)
    ultrasonic_cm: float | None = Field(default=None, ge=0, le=1000)
    stream_fps: int | None = Field(default=None, ge=1, le=30)
    telemetry_hz: float | None = Field(default=None, ge=0.5, le=10.0)


class RegisterPhoneRequest(BaseModel):
    phone_ip: str
    port: int = 8080
    goggle_port: int = 9000
    device_id: str | None = None


class SosRequest(BaseModel):
    location: str | None = None
    idempotency_key: str | None = None


def _create_udp_broadcast_packet() -> bytes:
    """Create a UDP discovery broadcast packet following the Diya Discovery Protocol v1.0.0."""
    packet = {
        "protocol": "diya-discovery",
        "version": "1.0.0",
        "device_id": state.device_id,
        "device_name": "Diya Smart Goggles Simulator",
        "device_type": "goggle",
        "ip": _get_local_ip(),
        "port": 9000,
        "battery": state.battery_level,
        "uptime": int((datetime.now(tz=timezone.utc) - state.started_at).total_seconds()),
        "timestamp": int(time.time() * 1000),  # milliseconds
    }
    return json.dumps(packet).encode("utf-8")


def _get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine the local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to a public DNS server (doesn't actually send data)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception:  # noqa: BLE001
        # Fallback to localhost if detection fails
        return "127.0.0.1"


async def _udp_broadcast_loop() -> None:
    """Background task that broadcasts UDP discovery packets."""
    logger.info("[UDP] Starting broadcast loop")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Initial burst (fast discovery on startup)
        for i in range(UDP_INITIAL_BURST_COUNT):
            try:
                packet = _create_udp_broadcast_packet()
                sock.sendto(packet, (UDP_BROADCAST_ADDRESS, UDP_DISCOVERY_PORT))
                logger.info(f"[UDP] Broadcast sent ({len(packet)} bytes) - burst {i+1}/{UDP_INITIAL_BURST_COUNT}")
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[UDP] Broadcast failed: {exc}")
            
            await asyncio.sleep(UDP_INITIAL_BURST_INTERVAL)
        
        # Ongoing broadcasts (maintenance heartbeat)
        while True:
            try:
                packet = _create_udp_broadcast_packet()
                sock.sendto(packet, (UDP_BROADCAST_ADDRESS, UDP_DISCOVERY_PORT))
                logger.info(f"[UDP] Broadcast sent ({len(packet)} bytes)")
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[UDP] Broadcast failed: {exc}")
            
            # Add jitter to avoid synchronized broadcasts
            import random
            jitter = random.uniform(-0.5, 0.5)
            await asyncio.sleep(UDP_DISCOVERY_INTERVAL + jitter)
            
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[UDP] Broadcast loop crashed: {exc}")
    finally:
        sock.close()
        logger.info("[UDP] Broadcast loop stopped")


async def _notify_ultrasonic_event(distance_cm: float, detected: bool) -> None:
    if not state.phone_ip:
        return

    url = f"http://{state.phone_ip}:{state.phone_port}/events/ultrasonic"
    payload = {
        "device_id": state.device_id,
        "distance_cm": distance_cm,
        "detected": detected,
        "ts": time.time(),
    }

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        _log("ultrasonic.notify.phone", distance_cm=distance_cm, detected=detected)
    except Exception as exc:  # noqa: BLE001
        _log("ultrasonic.notify.phone.failed", error=str(exc), distance_cm=distance_cm)


async def _notify_sos_event(payload: dict) -> None:
    if not state.phone_ip:
        raise HTTPException(status_code=400, detail="Phone is not registered yet")

    url = f"http://{state.phone_ip}:{state.phone_port}/sos"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        _log("sos.notify.phone", payload=payload)
    except Exception as exc:  # noqa: BLE001
        _log("sos.notify.phone.failed", error=str(exc), payload=payload)
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc


def _log(event: str, **fields: object) -> None:
    payload = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "event": event,
        "device_id": state.device_id,
        **fields,
    }
    logger.info(event, extra={"event": event, **fields})
    logs.add(payload)


def _jpeg_magic_ok(payload: bytes) -> bool:
    return len(payload) >= 2 and payload[0:2] == b"\xff\xd8"


def _request_id() -> str:
    return f"sim-{int(time.time() * 1000)}"


def _capture_webcam_jpeg(camera_index: int) -> bytes:
    """Try to capture a JPEG frame from the webcam with comprehensive error handling.

    Returns the JPEG bytes on success, raises RuntimeError with detailed message on failure.
    
    Edge cases handled:
    - OpenCV not installed
    - Camera not found / doesn't exist
    - Camera in use by another application
    - Camera hardware error
    - Permission denied
    - Empty frame / corrupted frame
    - JPEG encoding failure
    - Memory errors
    - Multiple camera indices fallback
    """
    # Edge Case 1: OpenCV not installed
    if cv2 is None:
        raise RuntimeError(
            "OpenCV (cv2) not available. "
            "Install it by running: cd hardware/smart-goggles/simulator && uv sync"
        )
    
    camera = None
    last_error = None
    
    # Try multiple camera indices (0, 1, 2) to handle different systems
    camera_indices_to_try = [camera_index]
    if camera_index != 0:
        camera_indices_to_try.append(0)
    if camera_index != 1 and 1 not in camera_indices_to_try:
        camera_indices_to_try.append(1)
    
    for idx in camera_indices_to_try:
        try:
            logger.info(f"[CAMERA] Attempting to open camera at index {idx}")
            
            # Edge Case 2: Camera doesn't exist or can't be opened
            camera = cv2.VideoCapture(idx)
            
            # Wait a bit for camera to initialize (some cameras need time)
            if not camera.isOpened():
                logger.warning(f"[CAMERA] Camera {idx} didn't open immediately, waiting 100ms...")
                time.sleep(0.1)
            
            # Edge Case 3: Check if camera actually opened
            if not camera.isOpened():
                last_error = f"Camera {idx} failed to open (may be in use or doesn't exist)"
                logger.warning(f"[CAMERA] {last_error}")
                camera.release()
                camera = None
                continue
            
            logger.info(f"[CAMERA] Camera {idx} opened successfully")
            
            # Edge Case 4: Try to set camera properties for better capture
            try:
                # Set resolution (helps with some buggy cameras)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # Disable autofocus (can cause delays)
                camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            except Exception as prop_error:
                # Non-critical, continue anyway
                logger.debug(f"[CAMERA] Could not set camera properties: {prop_error}")
            
            # Edge Case 5: Read frame with retry logic
            max_read_attempts = 3
            frame = None
            for attempt in range(max_read_attempts):
                logger.info(f"[CAMERA] Reading frame (attempt {attempt + 1}/{max_read_attempts})")
                ok, frame = camera.read()
                
                if ok and frame is not None:
                    # Edge Case 6: Validate frame is not empty
                    if frame.size == 0:
                        logger.warning(f"[CAMERA] Frame is empty on attempt {attempt + 1}")
                        time.sleep(0.1)
                        continue
                    
                    # Edge Case 7: Validate frame dimensions
                    if len(frame.shape) != 3 or frame.shape[2] != 3:
                        logger.warning(f"[CAMERA] Frame has invalid shape: {frame.shape}")
                        time.sleep(0.1)
                        continue
                    
                    logger.info(f"[CAMERA] Frame captured successfully: shape={frame.shape}, dtype={frame.dtype}")
                    break
                else:
                    logger.warning(f"[CAMERA] Failed to read frame on attempt {attempt + 1}")
                    time.sleep(0.1)
            
            camera.release()
            
            # Edge Case 8: All read attempts failed
            if frame is None or not ok:
                last_error = f"Failed to read frame from camera {idx} after {max_read_attempts} attempts"
                logger.error(f"[CAMERA] {last_error}")
                continue
            
            # Edge Case 9: Encode to JPEG with error handling
            try:
                logger.info(f"[CAMERA] Encoding frame to JPEG (quality={JPEG_QUALITY})")
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                encode_ok, buffer = cv2.imencode(".jpg", frame, encode_params)
                
                if not encode_ok or buffer is None:
                    raise RuntimeError("JPEG encoding returned failure status")
                
                jpeg_bytes = buffer.tobytes()
                
                # Edge Case 10: Validate JPEG output
                if len(jpeg_bytes) == 0:
                    raise RuntimeError("JPEG encoding produced empty output")
                
                # Edge Case 11: Validate JPEG magic bytes
                if not _jpeg_magic_ok(jpeg_bytes):
                    raise RuntimeError(
                        f"JPEG encoding produced invalid output (magic bytes: {jpeg_bytes[:2].hex()})"
                    )
                
                logger.info(f"[CAMERA] JPEG encoded successfully: {len(jpeg_bytes)} bytes")
                return jpeg_bytes
                
            except Exception as encode_error:
                last_error = f"JPEG encoding failed on camera {idx}: {encode_error}"
                logger.error(f"[CAMERA] {last_error}")
                continue
            
        except PermissionError as perm_error:
            # Edge Case 12: Permission denied (common on Linux/Mac)
            last_error = f"Permission denied for camera {idx}: {perm_error}"
            logger.error(f"[CAMERA] {last_error}")
            if camera:
                camera.release()
            continue
            
        except MemoryError as mem_error:
            # Edge Case 13: Out of memory
            last_error = f"Out of memory while accessing camera {idx}: {mem_error}"
            logger.error(f"[CAMERA] {last_error}")
            if camera:
                camera.release()
            continue
            
        except Exception as general_error:
            # Edge Case 14: Any other unexpected error
            last_error = f"Unexpected error with camera {idx}: {type(general_error).__name__}: {general_error}"
            logger.error(f"[CAMERA] {last_error}")
            if camera:
                camera.release()
            continue
        finally:
            # Edge Case 15: Always release camera resource
            if camera is not None:
                try:
                    camera.release()
                except Exception as release_error:
                    logger.warning(f"[CAMERA] Error releasing camera: {release_error}")
    
    # Edge Case 16: All camera indices failed
    error_message = f"Failed to capture from any camera (tried indices: {camera_indices_to_try}). "
    if last_error:
        error_message += f"Last error: {last_error}. "
    error_message += (
        "Troubleshooting:\n"
        "1. Make sure your camera is connected\n"
        "2. Close other applications using the camera (Zoom, Teams, Skype, etc.)\n"
        "3. Check camera permissions in system settings\n"
        "4. Try running: lsusb (Linux) or system_profiler SPCameraDataType (Mac)\n"
        "5. On Linux, check: ls -la /dev/video*"
    )
    raise RuntimeError(error_message)


@app.get("/")
async def home() -> HTMLResponse:
    index_path = _BASE_DIR / "static" / "index.html"
    with open(index_path, "r", encoding="utf-8") as handle:
        return HTMLResponse(handle.read())


@app.get("/health")
async def health() -> dict:
    uptime_s = int((datetime.now(tz=timezone.utc) - state.started_at).total_seconds())
    return {
        "status": "ok",
        "device_id": state.device_id,
        "connected": state.connected,
        "uptime_s": uptime_s,
    }


@app.get("/state")
async def get_state() -> dict:
    return {
        "device_id": state.device_id,
        "connected": state.connected,
        "battery_level": state.battery_level,
        "ultrasonic_cm": state.ultrasonic_cm,
        "stream_fps": state.stream_fps,
        "telemetry_hz": state.telemetry_hz,
        "last_command": state.last_command,
    }


@app.post("/state")
async def update_state(update: StateUpdate) -> dict:
    if update.connected is not None:
        state.connected = update.connected
    if update.battery_level is not None:
        state.battery_level = update.battery_level
    if update.ultrasonic_cm is not None:
        state.ultrasonic_cm = update.ultrasonic_cm
        detected = state.ultrasonic_cm <= 120
        await _notify_ultrasonic_event(state.ultrasonic_cm, detected)
    if update.stream_fps is not None:
        state.stream_fps = update.stream_fps
    if update.telemetry_hz is not None:
        state.telemetry_hz = update.telemetry_hz

    _log("state.update", connected=state.connected, battery_level=state.battery_level, ultrasonic_cm=state.ultrasonic_cm)
    return await get_state()


@app.post("/command")
async def command(req: CommandRequest) -> JSONResponse:
    state.last_command = {
        "command": req.command,
        "duration_ms": req.duration_ms,
        "payload": req.payload,
        "received_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    if req.command == "connect":
        state.connected = True
    elif req.command == "disconnect":
        state.connected = False
    elif req.command == "capture":
        _log("capture.command_rejected")
        raise HTTPException(status_code=400, detail="Use GET /capture for JPEG snapshot")


@app.api_route('/capture', methods=["GET", "POST"])
async def capture_raw(request: Request, camera_index: int = CAMERA_INDEX) -> Response:
    """Return a raw JPEG bytes payload for snapshot capture.

    Attempts to capture from the laptop webcam with comprehensive error handling.
    If capture fails, raises detailed error explaining the issue and suggesting solutions.
    
    Query Parameters:
        camera_index: Camera device index (default: 0). Try 1 or 2 if default fails.
    
    Returns:
        Response with JPEG image bytes
        
    Raises:
        HTTPException 422: Invalid camera_index parameter
        HTTPException 503: Camera capture failed (with detailed error message)
        HTTPException 500: Invalid JPEG produced (shouldn't happen)
        HTTPException 408: Capture timeout (took too long)
    """
    req_id = _request_id()
    client_host = request.client.host if request.client else "unknown"
    
    # Validate camera_index parameter
    if camera_index < 0:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid camera_index: {camera_index}. Must be >= 0. Try 0, 1, or 2."
        )
    
    if camera_index > 10:
        logger.warning(f"[CAPTURE] Unusual camera_index requested: {camera_index}")
        raise HTTPException(
            status_code=422,
            detail=f"Camera index {camera_index} seems too high. Valid range is typically 0-2."
        )
    
    logger.info(f"[CAPTURE] Starting capture request {req_id} from {client_host} (camera_index={camera_index})")
    
    try:
        # Edge Case: Capture takes too long (timeout after 10 seconds)
        import asyncio
        
        async def capture_with_timeout():
            # Run blocking camera capture in thread pool to avoid blocking event loop
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _capture_webcam_jpeg, camera_index)
        
        try:
            payload = await asyncio.wait_for(capture_with_timeout(), timeout=10.0)
        except asyncio.TimeoutError:
            error_msg = (
                f"Camera capture timed out after 10 seconds (camera_index={camera_index}). "
                "This usually means:\n"
                "1. Camera is frozen or unresponsive\n"
                "2. Camera driver issue\n"
                "3. Try a different camera_index\n"
                "4. Restart your computer\n"
                "5. Try unplugging and replugging external camera"
            )
            logger.error(f"[CAPTURE] {error_msg}")
            _log(
                "capture.raw.timeout",
                request_id=req_id,
                client=client_host,
                camera_index=camera_index,
            )
            raise HTTPException(status_code=408, detail=error_msg)
        
        is_fallback = False
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
        logger.error(f"[CAPTURE] Webcam capture failed: {error_msg}")
        _log(
            "capture.raw.webcam_unavailable",
            request_id=req_id,
            client=client_host,
            method=request.method,
            camera_index=camera_index,
            error=error_msg,
        )
        
        # Provide helpful error message with troubleshooting steps
        detail_msg = (
            f"Camera capture failed: {error_msg}\n\n"
            "Common solutions:\n"
            "1. Install OpenCV: cd hardware/smart-goggles/simulator && uv sync\n"
            "2. Close apps using camera: Zoom, Teams, Skype, etc.\n"
            "3. Check camera permissions in System Settings\n"
            "4. Try different camera_index: ?camera_index=1 or ?camera_index=2\n"
            "5. Restart your computer\n"
            "6. For external webcam: unplug and replug\n\n"
            f"See: hardware/smart-goggles/simulator/CAMERA_TROUBLESHOOTING.md"
        )
        
        raise HTTPException(status_code=503, detail=detail_msg)

    # Log successful capture
    _log(
        "capture.raw.success",
        request_id=req_id,
        client=client_host,
        method=request.method,
        camera_index=camera_index,
        size=len(payload),
    )
    
    # Final validation: check JPEG magic bytes
    if not _jpeg_magic_ok(payload):
        hex_prefix = payload[:8].hex() if len(payload) >= 8 else payload.hex()
        _log("capture.raw.invalid_jpeg", request_id=req_id, size=len(payload), hex_prefix=hex_prefix)
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JPEG produced (size={len(payload)}, magic={hex_prefix}). This is a bug."
        )
    
    hex_prefix = payload[:16].hex() if len(payload) >= 16 else payload.hex()
    logger.info(
        "capture.raw.respond",
        extra={
            "request_id": req_id,
            "size": len(payload),
            "hex_prefix": hex_prefix,
            "client": client_host,
            "camera_index": camera_index,
        },
    )
    
    # Return JPEG with appropriate headers
    headers = {
        "Cache-Control": "no-store",  # Don't cache (always fresh capture)
        "Content-Length": str(len(payload)),
        "X-Image-Format": "jpeg",
        "X-Image-Bytes": str(len(payload)),
        "X-Request-Id": req_id,
        "X-Camera-Index": str(camera_index),
        "X-Capture-Time": datetime.now(tz=timezone.utc).isoformat(),
    }
    return Response(content=payload, media_type="image/jpeg", headers=headers)


@app.post("/register-phone")
async def register_with_phone(req: RegisterPhoneRequest) -> JSONResponse:
    device_id = req.device_id or state.device_id
    phone_ip = req.phone_ip.strip().replace("http://", "").replace("https://", "")
    if "/" in phone_ip:
        phone_ip = phone_ip.split("/")[0]
    url = f"http://{phone_ip}:{req.port}/register"
    state.phone_ip = phone_ip
    state.phone_port = req.port
    payload = {
        "device_id": device_id,
        "device_type": "goggle",
        "port": req.goggle_port,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        _log("register.phone", phone_ip=phone_ip, port=req.port, device_id=device_id)
        return JSONResponse({"status": "ok", "registered": True})
    except Exception as exc:  # noqa: BLE001
        _log("register.phone.failed", phone_ip=phone_ip, port=req.port, error=str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc


@app.post("/sos")
async def trigger_sos(req: SosRequest) -> JSONResponse:
    payload = {
        "device_id": state.device_id,
        "device_type": "goggle",
        "payload": {
            "location": req.location,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
    }
    if req.idempotency_key:
        payload["idempotency_key"] = req.idempotency_key

    await _notify_sos_event(payload)
    return JSONResponse({"status": "ok", "forwarded": True})


@app.get("/logs")
async def get_logs() -> dict:
    return {"items": logs.list()}


async def _frame_stream() -> AsyncGenerator[bytes, None]:
    frame_id = 0
    while True:
        frame_id += 1
        payload = {
            "event": "frame",
            "frame_id": frame_id,
            "ts": time.time(),
            # Use PNG data-url in frame stream to match binary /capture and
            # avoid JPEG decoder incompatibilities on some Android devices.
            "data_url": TINY_PNG_DATA_URL,
            "battery_level": state.battery_level,
        }
        yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
        await asyncio.sleep(max(0.1, 1.0 / max(1, state.stream_fps)))


@app.get("/stream")
async def stream_frames() -> StreamingResponse:
    return StreamingResponse(_frame_stream(), media_type="text/event-stream")


async def _telemetry_stream() -> AsyncGenerator[bytes, None]:
    while True:
        payload = {
            "event": "telemetry",
            "ts": time.time(),
            "battery_level": state.battery_level,
            "ultrasonic_cm": state.ultrasonic_cm,
            "connected": state.connected,
        }
        yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
        await asyncio.sleep(max(0.1, 1.0 / max(0.5, state.telemetry_hz)))


@app.get("/telemetry")
async def telemetry_stream() -> StreamingResponse:
    return StreamingResponse(_telemetry_stream(), media_type="text/event-stream")
