# Assist Multimodal Testing Procedure

**Date**: June 20, 2026  
**Branch**: `fix/assist-gemini-multimodal`  
**Status**: Ready for Testing

---

## Overview

This document provides step-by-step testing procedures for the Assist multimodal image analysis feature after adding comprehensive diagnostics.

**Goal**: Identify root cause of Assist hanging issue through evidence collection.

---

## Prerequisites

### Backend
- ✅ Diagnostics deployed (`fix/assist-gemini-multimodal` branch)
- ✅ Gemini API key configured
- ✅ Docker environment running

### Flutter
- ✅ App built and connected to backend
- ✅ Device or emulator with camera
- ✅ Authentication working

### Tools
- Terminal for viewing backend logs
- Test images (JPEG files)
- Network connectivity to Gemini API

---

## Test 1: Isolated Backend Test

**Purpose**: Verify Gemini multimodal works independently of Flutter.

### Step 1: Prepare Test Image

```bash
# Download or use any JPEG image
# Example: test_image.jpg (should be a valid JPEG)

# Verify it's a valid JPEG
file test_image.jpg
# Expected: test_image.jpg: JPEG image data
```

### Step 2: Run Test Script

```bash
cd backend/api

# Test with a valid image
python scripts/test_multimodal.py path/to/test_image.jpg

# Test error handling
python scripts/test_multimodal.py --test-errors
```

### Expected Output (Success)

```
======================================================================
🧪 Gemini Multimodal Test Script
======================================================================

📁 Loading image: test_image.jpg
   Size: 45123 bytes (44.06 KB)
   JPEG magic valid: True
   First 16 bytes: ffd8ffe000104a46494600010101...

🔑 Using API key: YOUR_KEY...
📦 Using model: gemini-2.5-flash

🚀 Creating Gemini provider...

🔍 Analyzing image with Gemini...

✅ Success!

📝 Analysis Result:
   Provider: gemini
   Model: gemini-2.5-flash
   Latency: 1234ms

💬 Spoken Text:
   [Analysis of your image]

📄 Display Text:
   [Short summary]

⚠️  Hazards: None detected
🔍 Detected Objects: [list]
📊 Confidence: 0.85

======================================================================
✅ All tests passed!
======================================================================
```

### Expected Output (Error Handling)

```
🧪 Testing with invalid data...

   Test 1: Empty bytes
   ✅ Correctly rejected: MalformedResponseError

   Test 2: Invalid JPEG bytes
   ✅ Correctly rejected: MalformedResponseError

✅ Error handling works correctly
```

### If Test Fails

**Symptoms**: Network error, API error, timeout

**Actions**:
1. Check internet connectivity
2. Verify API key is correct
3. Check API quota/rate limits
4. Test with `curl` to verify network:
   ```bash
   curl https://generativelanguage.googleapis.com/
   ```

---

## Test 2: End-to-End Flutter Test

**Purpose**: Capture image from Flutter and analyze with backend.

### Step 1: Start Backend with Logging

```bash
cd backend/api

# Start with verbose logging
docker-compose up

# OR if running locally
uvicorn app.main:app --reload --log-level=info
```

**Monitor logs in terminal**.

### Step 2: Start Flutter App

```bash
cd apps/flutter

flutter run --debug
```

### Step 3: Trigger Assist

1. Open Flutter app
2. Navigate to home/assist screen
3. **Press Assist button**
4. **Capture or select an image**

### Step 4: Monitor Backend Logs

**Watch for these log sequences**:

#### ✅ Expected Success Flow

```
[ROUTER] Received image upload
[ROUTER]   Filename: image.jpg
[ROUTER]   Content-Type: image/jpeg
[ROUTER]   Size: 45123 bytes
[ROUTER] Image magic bytes: ffd8 (JPEG: True)

[SERVICE] Starting assist analysis
[SERVICE]   Session: abc-123
[SERVICE]   Intent: describe_scene
[SERVICE]   Image size: 45123 bytes
[SERVICE]   MIME: image/jpeg

[GEMINI] Image diagnostics:
[GEMINI]   Size: 45123 bytes
[GEMINI]   MIME: image/jpeg
[GEMINI]   Intent: describe_scene
[GEMINI]   First 16 bytes (hex): ffd8ffe000104a46494600010101...
[GEMINI]   JPEG magic valid: True
[GEMINI] Image validation passed, proceeding to API call

[GEMINI] Calling Gemini API with model: gemini-2.5-flash
[GEMINI] Gemini analysis completed

[SERVICE] Assist analysis completed
[SERVICE]   Latency: 1234ms
[SERVICE]   Provider: gemini
```

#### ❌ Failure: Empty Image

```
[ROUTER] Received image upload
[ROUTER]   Size: 0 bytes
[ROUTER] Image too small: 0 bytes
[ROUTER] Empty image received from client

ERROR: Returning 400 - Empty image data
```

**Root Cause**: Flutter sent empty bytes  
**Fix Needed**: Flutter image capture implementation

#### ❌ Failure: Invalid JPEG

```
[ROUTER] Image magic bytes: 0000 (JPEG: False)

[SERVICE] Starting assist analysis

[GEMINI] Image diagnostics:
[GEMINI]   Size: 1234 bytes
[GEMINI]   JPEG magic valid: False
[GEMINI] Invalid JPEG magic bytes. Expected: ff d8, Got: 00 00

ERROR: MalformedResponseError: Invalid JPEG format
```

**Root Cause**: Image data corrupted or not JPEG  
**Fix Needed**: Verify Flutter sends valid JPEG

#### ❌ Failure: Gemini Rejects Image

```
[GEMINI] Image validation passed, proceeding to API call
[GEMINI] Calling Gemini API

ERROR: Gemini APIError: code=400, message=Unable to process input image
```

**Root Cause**: Gemini cannot process this specific image  
**Possible Issues**:
- Image format not supported by Gemini
- Image dimensions invalid
- Image corrupted in subtle way

### Step 5: Analyze Results

Record findings:

| Test | Image Size | JPEG Valid | Gemini Response | Result |
|------|-----------|------------|----------------|---------|
| 1    | XXXX bytes | True/False | Success/Error | ✅/❌ |
| 2    | XXXX bytes | True/False | Success/Error | ✅/❌ |
| 3    | XXXX bytes | True/False | Success/Error | ✅/❌ |

---

## Test 3: Flutter Image Capture Investigation

**Purpose**: Verify Flutter is sending valid image data.

### Check Flutter Implementation

1. Open `apps/flutter/lib/features/assist/infrastructure/`
2. Find image capture code
3. Verify:
   - Image is captured as JPEG
   - Bytes are not empty
   - File is read correctly
   - Multipart encoding is correct

### Add Flutter Logging

```dart
// Before sending to backend
final bytes = await imageFile.readAsBytes();
print('[FLUTTER] Image captured:');
print('[FLUTTER]   Size: ${bytes.length} bytes');
print('[FLUTTER]   JPEG magic: ${bytes.length >= 2 && bytes[0] == 0xFF && bytes[1] == 0xD8}');
if (bytes.length >= 16) {
  print('[FLUTTER]   First 16 bytes: ${bytes.sublist(0, 16).map((b) => b.toRadixString(16).padLeft(2, '0')).join('')}');
}
```

### Test Different Image Sources

1. **Camera capture**: Take photo with device camera
2. **Gallery selection**: Select existing photo
3. **Simulator/Goggle**: Capture from simulator HTTP endpoint

Compare results for each source.

---

## Test 4: Network Investigation

**Purpose**: Verify network path from Flutter → Backend → Gemini.

### Test 1: Flutter → Backend

```bash
# From Flutter device/emulator
curl -X POST http://backend-ip:8000/api/v1/assist/sessions/test/turns \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "intent_json={\"type\":\"describe_scene\"}" \
  -F "trigger_json={\"source\":\"manual\"}" \
  -F "client_context_json={}" \
  -F "image_file=@test_image.jpg"
```

**Expected**: Backend logs show image received.

### Test 2: Backend → Gemini

Already tested in Test 1 (isolated backend test).

### Test 3: Docker Networking

```bash
# Inside backend container
docker exec -it diya-backend-1 bash

# Test external connectivity
curl -I https://generativelanguage.googleapis.com/

# Expected: 200 or 404 (proves connectivity)
```

---

## Troubleshooting Guide

### Issue 1: Empty Image in Logs

**Symptoms**:
```
[ROUTER] Size: 0 bytes
```

**Root Cause**: Flutter not capturing/sending image  
**Actions**:
1. Check Flutter logs for capture errors
2. Verify camera permissions
3. Test with gallery selection
4. Check multipart encoding in Flutter

### Issue 2: Invalid JPEG Magic

**Symptoms**:
```
[GEMINI] JPEG magic valid: False
```

**Root Cause**: Image corrupted or wrong format  
**Actions**:
1. Check first 16 bytes in logs
2. Verify Flutter saves as JPEG
3. Test with different image source
4. Check image processing pipeline

### Issue 3: Gemini Rejects Valid Image

**Symptoms**:
```
Gemini APIError: code=400
```

**Root Cause**: Image doesn't meet Gemini requirements  
**Actions**:
1. Check image dimensions
2. Check image file size
3. Try smaller/different image
4. Check Gemini API documentation

### Issue 4: Network Timeout

**Symptoms**:
```
TimeoutError: Gemini request timed out
```

**Root Cause**: Network latency or large image  
**Actions**:
1. Check internet connectivity
2. Check image size (should be <5MB)
3. Increase timeout in provider
4. Test with smaller image

### Issue 5: Backend Never Receives Request

**Symptoms**: No logs at all

**Root Cause**: Flutter→Backend connection issue  
**Actions**:
1. Verify backend URL in Flutter
2. Check authentication token
3. Check network connectivity
4. Test with curl

---

## Success Criteria

### ✅ Test Passes If:
- [ ] Backend logs show image received
- [ ] Image size > 0 bytes
- [ ] JPEG magic valid (ff d8)
- [ ] Gemini analysis completes
- [ ] Response returned to Flutter
- [ ] TTS speaks result
- [ ] UI stops spinning

### ❌ Test Fails If:
- [ ] Backend never receives image
- [ ] Image is empty
- [ ] JPEG magic invalid
- [ ] Gemini rejects image
- [ ] Timeout occurs
- [ ] UI hangs indefinitely

---

## Evidence Collection

### Required Logs

1. **Backend logs** (full session):
   ```bash
   docker-compose logs -f backend > assist_test_logs.txt
   ```

2. **Flutter logs**:
   ```bash
   flutter logs > flutter_assist_logs.txt
   ```

3. **Test results**: Fill in template:
   ```
   Date: YYYY-MM-DD
   Branch: fix/assist-gemini-multimodal
   Device: Android/iOS/Desktop
   
   Backend Logs:
   - Image received: Yes/No
   - Image size: XXXX bytes
   - JPEG valid: Yes/No
   - Gemini response: Success/Error
   
   Flutter Logs:
   - Image captured: Yes/No
   - Image size: XXXX bytes
   - Request sent: Yes/No
   - Response received: Yes/No
   
   Result: Success/Failure
   Root Cause: [Description]
   ```

---

## Next Steps Based on Results

### If Multimodal Works (Isolated Test Passes)
→ Issue is in Flutter→Backend integration  
→ Focus on multipart encoding, image capture

### If Image is Empty
→ Issue is in Flutter image capture  
→ Check camera permissions, file reading

### If Image is Invalid JPEG
→ Issue is in image processing pipeline  
→ Check format conversion, compression

### If Gemini Rejects Valid Image
→ Issue is Gemini API compatibility  
→ Check image specs, try different formats

### If Network Timeout
→ Issue is connectivity or image size  
→ Check network, reduce image size

---

## Status

**Current Phase**: Ready for Testing  
**Waiting For**: Human to execute tests and collect evidence  
**Blocked**: No  

**DO NOT** declare issue "fixed" until:
1. All tests pass
2. Assist works end-to-end
3. Multiple images tested successfully
4. No regressions observed

---

**Last Updated**: June 20, 2026  
**Branch**: fix/assist-gemini-multimodal  
**Status**: READY FOR HUMAN VERIFICATION
