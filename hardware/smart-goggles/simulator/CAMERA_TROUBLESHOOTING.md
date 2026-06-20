# Camera Troubleshooting Guide

## Issue: Simulator Returns Error Instead of Camera Image

If the simulator is returning an error when you try to capture an image, follow these steps:

### Step 1: Check OpenCV Installation

Make sure OpenCV is installed:

```bash
cd hardware/smart-goggles/simulator
uv sync
```

This will install `opencv-python` and other dependencies.

### Step 2: Check Camera Access

Make sure your laptop camera is:
- ✅ Connected (for external webcams)
- ✅ Not being used by another application (Zoom, Teams, etc.)
- ✅ Enabled in system settings

**Windows**: Check Settings → Privacy → Camera  
**macOS**: Check System Preferences → Security & Privacy → Camera  
**Linux**: Check `/dev/video0` exists

### Step 3: Test Camera Manually

Test if OpenCV can access your camera:

```python
python3 -c "import cv2; cam = cv2.VideoCapture(0); print('Camera opened:', cam.isOpened()); cam.release()"
```

Expected output: `Camera opened: True`

### Step 4: Try Different Camera Index

If you have multiple cameras, try different indices:

```bash
# Test with camera 0 (default)
curl http://localhost:9000/capture?camera_index=0 -o test0.jpg

# Test with camera 1
curl http://localhost:9000/capture?camera_index=1 -o test1.jpg
```

### Step 5: Check Simulator Logs

Start the simulator and watch the logs:

```bash
cd hardware/smart-goggles/simulator
uv run fastapi dev app/main.py
```

When you try to capture, you should see:
```
[CAMERA] Attempting to open camera 0
[CAMERA] Camera opened successfully
[CAMERA] Frame captured: (480, 640, 3)
[CAMERA] JPEG encoded: 45632 bytes
```

If you see errors, they'll tell you what's wrong.

### Common Issues

#### Issue: "OpenCV not available"

**Solution**: Install opencv-python
```bash
uv sync
# or
pip install opencv-python
```

#### Issue: "Failed to open webcam"

**Solutions**:
1. Close other applications using the camera (Zoom, Teams, Skype)
2. Check camera permissions in system settings
3. Try a different camera index
4. Restart your computer
5. For external webcam: unplug and replug

#### Issue: "Failed to read frame from webcam"

**Solutions**:
1. Camera driver issue - update camera drivers
2. Try a different camera
3. Check `/dev/video*` permissions on Linux

#### Issue: Camera works in other apps but not simulator

**Solutions**:
1. Check if Python has camera permissions
2. Try running simulator with sudo (Linux/Mac)
3. Check firewall/antivirus blocking Python

### Test the Fix

After applying fixes:

1. Start the simulator:
```bash
cd hardware/smart-goggles/simulator
uv run fastapi dev app/main.py
```

2. Open browser: `http://localhost:9000`

3. Click "Capture Image" or use curl:
```bash
curl http://localhost:9000/capture -o test.jpg
open test.jpg  # macOS
start test.jpg  # Windows
xdg-open test.jpg  # Linux
```

You should see your camera image, not a red square!

---

## Recent Changes

The simulator now:
- ✅ Provides detailed error messages
- ✅ Tries camera index 0 as fallback
- ✅ Logs every step of capture process
- ✅ Raises errors instead of silently returning red image
- ✅ Suggests solutions in error messages

This makes it easier to diagnose camera issues!
