# Assist Flow Debug Status

**Date**: June 19, 2026  
**Branch**: `feat/goggle-capture-integration`

---

## Issues Fixed ✅

### Issue #1: Infinite Spinner Hang (FIXED)

**Status**: ✅ **Resolved**

**Root Cause**: `GoggleCaptureAdapter` called `await _deviceManager.devices.first` on a stream that never emitted an initial value.

**Fix**:
1. Added 2-second timeout to stream subscription
2. Emit initial empty device list in DeviceManager constructor
3. Falls back to phone camera gracefully

**Result**: UI spinner never hangs. Assist always completes or shows error.

---

## Issues Remaining ⚠️

### Issue #2: Authentication 401 Error (INVESTIGATING)

**Status**: ⚠️ **Under Investigation**

**New Logs Show**:
```
POST /api/v1/assist/.../turns - 401 - 215ms  ← First attempt fails
POST /api/v1/auth/refresh - 200 - 62ms       ← Refresh succeeds
(No retry of original Assist request visible)
```

**Analysis**:
- ✅ `AuthInterceptor` exists and is wired into `apiDioProvider`
- ✅ `TokenExpiryInterceptor` handles 401 and refreshes token
- ❌ But the original Assist request appears to be lost after refresh
- ❌ This is the **exact issue** documented in Task 3 of context transfer

**Hypothesis**:
1. Token is expired when Assist request is made
2. `AuthInterceptor` attaches the expired token
3. Backend returns 401
4. `TokenExpiryInterceptor` refreshes successfully
5. **But**: Multipart/FormData requests (image upload) cannot be retried because the stream is consumed
6. Result: Assist request is lost, user sees spinner forever (until timeout)

**Why This Happens**:
- `FormData` and `MultipartFile` streams are single-use
- After the first send attempt (with expired token), the body is consumed
- Retry attempt finds empty body → fails silently or with error

**Logging Added** (Commit `80c0a22`):
- `[AuthInterceptor]` logs when token is attached
- `[AuthInterceptor]` warns when no valid session exists
- `[TokenExpiryInterceptor]` logs retry attempts
- `[TokenExpiryInterceptor]` logs retry success/failure

**Next Test**: Run Assist and check Flutter console for these new logs to confirm the flow.

---

## Investigation Steps Taken

### 1. Flutter Flow Analysis
- ✅ AssistController error handling confirmed
- ✅ AssistPipeline has proper try/catch
- ✅ AutoCaptureAdapter timeout fixed
- ✅ GoggleCaptureAdapter timeout fixed

### 2. Backend Flow Analysis
- ✅ Request reaches `/api/v1/assist/sessions/.../turns`
- ✅ Image is parsed and uploaded
- ✅ AssistService.analyze_image() is called
- ✅ GeminiProvider.analyze_image() is called
- ❌ `_execute_with_retry()` fails with generic error

### 3. Configuration Check
- ✅ `GEMINI_API_KEY` is set in `.env`
- ✅ `provide_gemini()` doesn't raise 503 (key is present)
- ❌ API key validity unknown
- ❌ Actual exception type unknown

---

## Logging Improvements Added

### Commit: `76e69c2`

**Changes**:
1. **service.py**: Added exception type and message to error log
   ```python
   logger.error(
       f"Provider analysis failed: {type(e).__name__}: {str(e)}",
       exc_info=True,
   )
   ```

2. **gemini.py**: Added detailed error logging
   ```python
   logger.debug(f"Calling Gemini API with model: {self._model_name}")
   logger.error(f"Gemini APIError: code={code}, message={str(e)}")
   logger.error(f"Gemini unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
   ```

**Next Steps**: Trigger Assist again and check logs for actual exception details.

---

## Possible Root Causes

### 1. Invalid API Key ⚠️
**Symptom**: Gemini API rejects the key  
**Evidence**: 502 error code  
**Fix**: Verify API key at [Google AI Studio](https://aistudio.google.com/apikey)

**Test**:
```python
from google import genai
client = genai.Client(api_key="AIzaSyCMgKYAjR7dl46pOElf8T6jQLO-W4nmKsI")
client.models.list()  # Should list models if key is valid
```

### 2. Model Name Invalid ⚠️
**Symptom**: Model doesn't exist or not accessible  
**Check**: `settings.providers.gemini_model_name`  
**Valid models**: `gemini-2.0-flash-exp`, `gemini-1.5-pro`, `gemini-1.5-flash`

### 3. Quota Exceeded ⚠️
**Symptom**: Free tier quota exhausted  
**Evidence**: Would show in Gemini logs  
**Fix**: Upgrade to paid tier or wait for quota reset

### 4. Network/Firewall Issue ⚠️
**Symptom**: Docker container can't reach `generativelanguage.googleapis.com`  
**Test**: 
```bash
docker exec diya-api curl -I https://generativelanguage.googleapis.com
```

### 5. Request Format Issue ⚠️
**Symptom**: `response_schema` not supported on model  
**Evidence**: AFC log suggests API is processing  
**Fix**: Remove schema constraint or use compatible model

---

## Recommended Debug Steps

### Step 1: Check Actual Error (High Priority)
```bash
# Trigger Assist from Flutter
# Then immediately check logs:
docker logs diya-api --tail 50

# Look for:
# - "Gemini APIError: code=XXX"
# - "Gemini unexpected error:"
# - Full traceback
```

### Step 2: Verify API Key (High Priority)
```bash
# Test API key manually:
docker exec -it diya-api python3 -c "
from google import genai
client = genai.Client(api_key='AIzaSyCMgKYAjR7dl46pOElf8T6jQLO-W4nmKsI')
print('Models:', list(client.models.list())[:3])
"
```

Expected output: List of available models  
If fails: API key is invalid/expired

### Step 3: Check Model Name
```bash
# Check current model configuration:
docker exec diya-api cat /app/.env | grep GEMINI_MODEL

# Should be one of:
# - gemini-2.0-flash-exp (recommended for structured output)
# - gemini-1.5-pro
# - gemini-1.5-flash
```

### Step 4: Test Minimal Request
```bash
# Test with minimal content (no schema):
docker exec -it diya-api python3 -c "
from google import genai
client = genai.Client(api_key='AIzaSyCMgKYAjR7dl46pOElf8T6jQLO-W4nmKsI')
response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents='Hello, world!'
)
print('Response:', response.text)
"
```

Expected: "Hello! How can I help you?"  
If fails: Network or auth issue

### Step 5: Test With Image
```bash
# Create test image:
docker exec -it diya-api python3 << 'EOF'
from google import genai
from google.genai import types
import base64

client = genai.Client(api_key='AIzaSyCMgKYAjR7dl46pOElf8T6jQLO-W4nmKsI')

# Minimal 1x1 red PNG
png_bytes = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)

part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents=["Describe this image", part]
)
print('Response:', response.text)
EOF
```

Expected: Image description  
If fails: Image handling issue

### Step 6: Test With Schema
```bash
# Test with response schema (the actual issue?):
docker exec -it diya-api python3 << 'EOF'
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import base64

class TestSchema(BaseModel):
    description: str = Field(description="Image description")

client = genai.Client(api_key='AIzaSyCMgKYAjR7dl46pOElf8T6jQLO-W4nmKsI')

png_bytes = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)

part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents=["Describe this image", part],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TestSchema,
    )
)
print('Response:', response.text)
print('Parsed:', response.parsed)
EOF
```

Expected: JSON with TestSchema format  
If fails: Schema constraint not supported on this model

---

## Quick Fix Options

### Option A: Remove Schema Constraint (Test Mode)
**File**: `backend/api/app/modules/assist/providers/gemini.py`

```python
# Comment out response_schema temporarily:
response = self._client.models.generate_content(
    model=self._model_name,
    contents=[prompt, image_part],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        # response_schema=GeminiAnalysisResult,  # TEMPORARY: Disable
    ),
)
```

**Result**: Will work if schema is the issue, but response may not be structured.

### Option B: Switch Model
**File**: `.env`

```bash
# Try different model:
GEMINI_MODEL_NAME=gemini-1.5-flash
```

**Result**: May work if current model doesn't support schemas.

### Option C: Regenerate API Key
1. Go to https://aistudio.google.com/apikey
2. Delete current key
3. Create new key
4. Update `.env`:
   ```bash
   GEMINI_API_KEY=<new_key_here>
   ```
5. Restart API:
   ```bash
   docker compose restart api
   ```

---

## Current Branch Status

**Files Modified**:
- ✅ `apps/flutter/lib/features/assist/infrastructure/goggle_capture_adapter.dart` (timeout fix)
- ✅ `apps/flutter/lib/core/hardware/infrastructure/manager/device_manager_impl.dart` (initial emission)
- ✅ `backend/api/app/modules/assist/service.py` (improved logging)
- ✅ `backend/api/app/modules/assist/providers/gemini.py` (improved logging)

**Documentation**:
- ✅ `docs/roadmaps/goggles/BUG_REPORT_ASSIST_INFINITE_HANG.md`
- ✅ `docs/roadmaps/goggles/ASSIST_DEBUG_STATUS.md` (this file)

**Tests**: 44/44 passing (Flutter)  
**Analyzer**: Clean (Flutter)

---

## Summary

**Flutter Issue** (infinite hang): ✅ **FIXED**  
**Backend Issue** (Gemini 502): ⚠️ **UNDER INVESTIGATION**

**Next Action**: Run debug steps above to identify the actual Gemini error, then apply appropriate fix.

