# Diya Smart Goggle Firmware V1

ESP32-S3 firmware for Diya Smart Goggles - simulator-compatible WiFi device.

## Hardware Requirements

- **Board**: ESP32-S3 DevKit (with PSRAM)
- **Camera**: OV5640 or OV5643
- **Buttons**: 2x tactile buttons (GPIO 21 & 47)
- **Power**: USB-C

## Features

### ✅ Implemented
- WiFi connectivity with auto-reconnect
- HTTP REST API (simulator-compatible)
- Camera capture (1024x768 JPEG)
- Button input (Assist + SOS)
- Button events (single, double, long press)
- Telemetry (WiFi RSSI, heap, uptime)
- Phone registration
- Heavy logging for debugging
- Graceful failure recovery

### ⏳ Postponed (Future Versions)
- Battery integration (hardcoded to 75%)
- OTA updates
- BLE connectivity
- Video streaming
- Audio output
- Edge AI

## API Endpoints (Simulator Compatible)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Device info page |
| GET | `/health` | Health check |
| GET | `/state` | Device state + telemetry |
| GET | `/capture` | Capture JPEG image |
| POST | `/register-phone` | Register with phone |
| POST | `/command` | Send commands |

## Setup Instructions

### 1. Install PlatformIO

```bash
# VS Code Extension
# Install "PlatformIO IDE" from VS Code extensions

# OR CLI
pip install platformio
```

### 2. Configure WiFi

Edit `src/config.h`:

```cpp
#define DEFAULT_WIFI_SSID "Your-WiFi-SSID"
#define DEFAULT_WIFI_PASSWORD "Your-WiFi-Password"
```

### 3. Build and Upload

```bash
cd hardware/smart-goggles/firmware

# Build
pio run

# Upload
pio run --target upload

# Monitor serial output
pio device monitor
```

### 4. Find Device IP

Watch serial monitor for:
```
[WIFI] IP Address: 192.168.1.xxx
```

### 5. Test Endpoints

```bash
# Health check
curl http://192.168.1.xxx:9000/health

# Capture image
curl http://192.168.1.xxx:9000/capture --output test.jpg

# Get state
curl http://192.168.1.xxx:9000/state
```

## Pin Configuration

### Camera Pins (OV5640)
```cpp
XCLK  = GPIO 15
SIOD  = GPIO 4  (SDA)
SIOC  = GPIO 5  (SCL)
D0-D7 = GPIO 11, 9, 8, 10, 12, 18, 17, 16
VSYNC = GPIO 6
HREF  = GPIO 7
PCLK  = GPIO 13
```

### Button Pins
```cpp
Assist Button = GPIO 21 (INPUT_PULLUP)
SOS Button    = GPIO 47 (INPUT_PULLUP)
```

## Button Events

### Event Types
- **Single Press**: Quick tap
- **Double Press**: Two taps within 400ms
- **Long Press**: Hold for 1000ms+

### Event Format
```json
{
  "type": "button",
  "button": "assist" | "sos",
  "event": "single_press" | "double_press" | "long_press",
  "timestamp": 123456
}
```

## Telemetry

### GET /state Response
```json
{
  "device_id": "goggle-abc123",
  "connected": true,
  "battery_level": 75,
  "telemetry": {
    "battery": 75,
    "wifi_rssi": -54,
    "uptime": 12345,
    "heap_free": 120000,
    "heap_min": 94000,
    "camera": "ok",
    "buttons": "ok",
    "ip": "192.168.1.100",
    "captures": 35,
    "capture_failures": 1
  }
}
```

## Logging

Serial output (115200 baud) provides detailed logs:

```
[INIT] Device state initialized
[INIT] Telemetry initialized
[INIT] Buttons initialized
[CAMERA] Initializing...
[CAMERA] Initialized successfully
[WIFI] Connecting to WiFi...
[WIFI] Connected!
[WIFI] IP Address: 192.168.1.100
[HTTP] Server started on port 9000
[READY] Smart Goggle is ready!
```

## Troubleshooting

### Camera Fails to Initialize
- Check pin connections
- Verify camera module power
- Check serial logs for error codes
- Try reducing JPEG quality in config.h

### WiFi Won't Connect
- Verify SSID/password in config.h
- Check 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Watch serial monitor for connection attempts

### Capture Returns Errors
- Camera may need reinitialization (automatic after 5 failures)
- Check heap memory (logged every 10s)
- Reduce image size if memory issues persist

### Heap Memory Low
- Reduce `fb_count` in camera config
- Lower JPEG quality
- Restart device

## Flutter Integration

### Device Registration Flow

1. Phone starts discovery server on port 8080
2. Goggle connects to phone's WiFi hotspot
3. Call `/register-phone` with phone's IP:
   ```bash
   curl -X POST http://goggle-ip:9000/register-phone \
     -H "Content-Type: application/json" \
     -d '{"phone_ip": "192.168.43.1", "port": 8080}'
   ```
4. Goggle sends registration to phone
5. Flutter DeviceManager detects goggle
6. Flutter can now communicate with goggle

### Flutter Compatibility

This firmware is a **drop-in replacement** for the simulator. Flutter code requires **zero changes**:

- Same API endpoints
- Same JSON schemas
- Same HTTP behavior
- Same error handling

## File Structure

```
firmware/
├── platformio.ini       # PlatformIO configuration
├── src/
│   ├── main.cpp         # Main program
│   ├── config.h         # Configuration constants
│   ├── camera_manager.h # Camera operations
│   ├── button_manager.h # Button event handling
│   ├── telemetry.h      # System telemetry
│   ├── device_state.h   # Device state management
│   └── http_server.h    # HTTP server & routes
└── README.md            # This file
```

## Development

### Debug Logging

Logging is enabled by default. To disable:

```cpp
// In config.h
#define ENABLE_VERBOSE_LOGGING 0
```

### Adjust Camera Quality

```cpp
// In config.h
#define CAMERA_FRAME_SIZE FRAMESIZE_SVGA  // 800x600 (smaller)
#define CAMERA_JPEG_QUALITY 15  // 0-63 (higher number = lower quality)
```

### Change HTTP Port

```cpp
// In config.h
#define HTTP_PORT 8080  // Default: 9000
```

## License

Same as parent Diya project.