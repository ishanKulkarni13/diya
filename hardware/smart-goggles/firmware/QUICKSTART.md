# Smart Goggle Firmware - Quick Start

## 5-Minute Setup

### 1. Hardware
- ESP32-S3 DevKit (with PSRAM)
- OV5640 camera module
- 2x buttons (GPIO 21 & 47)
- USB-C cable

### 2. Configure WiFi
Edit `src/config.h`:
```cpp
#define DEFAULT_WIFI_SSID "Your-WiFi-Name"
#define DEFAULT_WIFI_PASSWORD "Your-Password"
```

### 3. Build & Flash
```bash
cd hardware/smart-goggles/firmware
pio run --target upload
pio device monitor
```

### 4. Get IP Address
Watch serial monitor for:
```
[WIFI] IP Address: 192.168.1.xxx
```

### 5. Test
```bash
# Health check
curl http://192.168.1.xxx:9000/health

# Capture image
curl http://192.168.1.xxx:9000/capture -o test.jpg

# View image
open test.jpg  # macOS
start test.jpg # Windows
xdg-open test.jpg # Linux
```

## Camera Wiring (ESP32-S3 to OV5640)

| Signal | ESP32-S3 Pin | OV5640 Pin |
|--------|--------------|------------|
| XCLK | GPIO 15 | XCLK |
| SIOD (SDA) | GPIO 4 | SDA |
| SIOC (SCL) | GPIO 5 | SCL |
| D0 | GPIO 11 | D0 |
| D1 | GPIO 9 | D1 |
| D2 | GPIO 8 | D2 |
| D3 | GPIO 10 | D3 |
| D4 | GPIO 12 | D4 |
| D5 | GPIO 18 | D5 |
| D6 | GPIO 17 | D6 |
| D7 | GPIO 16 | D7 |
| VSYNC | GPIO 6 | VSYNC |
| HREF | GPIO 7 | HREF |
| PCLK | GPIO 13 | PCLK |
| 3V3 | 3V3 | VCC |
| GND | GND | GND |

## Button Wiring

| Button | ESP32-S3 Pin | Connection |
|--------|--------------|------------|
| Assist | GPIO 21 | Button → GND (internal pullup) |
| SOS | GPIO 47 | Button → GND (internal pullup) |

## Troubleshooting

### Camera Won't Initialize
- Check all 15+ connections
- Verify 3.3V power (not 5V!)
- Try power cycling
- Check serial logs for error code

### WiFi Won't Connect
- ESP32 only supports 2.4GHz (not 5GHz)
- Check SSID/password spelling
- Try moving closer to router

### Can't Upload Firmware
- Check USB cable (data cable, not charge-only)
- Hold BOOT button while plugging in
- Change upload_port in platformio.ini

### Image Quality Poor
- Adjust lighting
- Clean camera lens
- Modify CAMERA_JPEG_QUALITY in config.h

## Next Steps

1. ✅ Verify hardware works
2. Register with Flutter app (see README.md)
3. Test button events
4. Capture test images
5. Check text readability

**Full Documentation**: See [README.md](README.md) and [GOGGLE_FIRMWARE_V1.md](../../../docs/roadmaps/goggles/GOGGLE_FIRMWARE_V1.md)