# Smart Cane Firmware - Quick Test Guide

**Firmware Version**: 1.0.0  
**Last Updated**: June 20, 2026

---

## Hardware Setup

### Required Components
- ESP32 Dev Module
- HC-SR04 Ultrasonic Sensor
- LED (any color)
- 220Ω Resistor (for LED)
- Breadboard and jumper wires

### Wiring

```
HC-SR04 → ESP32
─────────────────
VCC     → 5V
GND     → GND
TRIG    → GPIO 18
ECHO    → GPIO 19 ⚠️ (needs voltage divider: 10kΩ + 20kΩ)

LED → ESP32
─────────────────
Anode (+)  → GPIO 23
Cathode (-) → 220Ω → GND
```

⚠️ **IMPORTANT**: HC-SR04 ECHO outputs 5V. ESP32 is 3.3V tolerant. Use voltage divider!

**Voltage Divider**:
```
ECHO (5V) ──┬── 10kΩ ──┬── GPIO 19
            │          │
            └── 20kΩ ──┴── GND
```
Output = 5V × (20kΩ/(10kΩ+20kΩ)) = 3.33V ✅

---

## Upload Firmware

### Using Arduino IDE

1. **Install ESP32 Board Support**:
   - File → Preferences
   - Additional Board Manager URLs: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Tools → Board → Boards Manager → Search "ESP32" → Install

2. **Configure Board**:
   - Tools → Board → ESP32 Arduino → ESP32 Dev Module
   - Tools → Upload Speed → 115200
   - Tools → Port → (select your COM port)

3. **Upload**:
   - Open `esp-32.ino`
   - Click Upload (→)
   - Wait for "Done uploading"

---

## Testing

### 1. Serial Monitor Test (5 minutes)

**Open Serial Monitor**:
- Tools → Serial Monitor
- Set baud rate: **115200**

**Expected Output**:
```
[INIT] Starting Diya Cane BLE Server...
[INIT] Pins - Button:0 Trig:18 Echo:19 LED:23
[BLE] Advertising started
[US] 200.5 cm (filtered: 200.5 cm)
[US] 198.3 cm (filtered: 199.8 cm)
[US] Invalid reading
[US] 195.2 cm (filtered: 197.1 cm)
```

**What to Check**:
- ✅ Initialization messages appear
- ✅ Ultrasonic readings update ~10 times/second
- ✅ Distance values are reasonable
- ✅ "Invalid reading" appears occasionally (normal for HC-SR04)

---

### 2. LED Haptic Test (2 minutes)

**Test Distance Ranges**:

| Test | Action | Expected LED |
|------|--------|--------------|
| 1 | Hold hand 200cm away | OFF |
| 2 | Move hand to 120cm | Slow blink (500ms) |
| 3 | Move hand to 80cm | Fast blink (200ms) |
| 4 | Move hand to 30cm | Solid ON |
| 5 | Move hand away to 200cm | OFF |

**Serial Output Should Show**:
```
[US] 200.5 cm (filtered: 200.5 cm)
[US] 120.3 cm (filtered: 160.2 cm)
[US] 80.1 cm (filtered: 120.1 cm)
[US] 30.5 cm (filtered: 75.3 cm)
```

**Tips**:
- Use a flat surface (book, cardboard) for better reflection
- Allow 1-2 seconds for EMA filter to stabilize
- LED should change smoothly as you move object

---

### 3. BLE Connection Test (3 minutes)

**Using nRF Connect App** (Android/iOS):

1. **Scan for Device**:
   - Open nRF Connect
   - Tap "Scan"
   - Find "DIYA_CANE_DEV"

2. **Connect**:
   - Tap "Connect"
   - Expected Serial Output:
     ```
     [BLE] Connected
     [HELLO] Sent handshake
     ```

3. **View Services**:
   - Expand service `1b050001-c852-4752-b883-fa4c0342ab01`
   - Find characteristic `1b050003-c852-4752-b883-fa4c0342ab01`
   - Tap "Enable notifications" (three down arrows icon)

4. **Verify Packets**:
   - **Hello** (immediately after connect):
     ```json
     {"v":1,"t":"hello","protocol":1,"firmware":"1.0.0"}
     ```
   
   - **Obstacle** (every 500ms):
     ```json
     {"v":1,"t":"obstacle","distance_cm":42.1,"detected":true}
     ```
   
   - **Heartbeat** (every 5 seconds):
     ```json
     {"v":1,"t":"heartbeat"}
     ```

5. **Test Button**:
   - Press BOOT button on ESP32
   - Expected packet:
     ```json
     {"v":1,"t":"button","button":1,"press":"single"}
     ```
   - Expected Serial Output:
     ```
     [BUTTON] Pressed
     ```

---

### 4. Obstacle Detection Test (2 minutes)

**Setup**:
- Connect via BLE (nRF Connect)
- Enable notifications on RX characteristic

**Test Cases**:

| Test | Distance | Expected `detected` | Expected LED |
|------|----------|---------------------|--------------|
| 1 | 200cm | `false` | OFF |
| 2 | 140cm | `true` | Slow blink |
| 3 | 80cm | `true` | Fast blink |
| 4 | 30cm | `true` | Solid ON |

**Verify**:
- ✅ `distance_cm` value matches Serial Monitor
- ✅ `detected` is `true` when distance ≤ 150cm
- ✅ Packets arrive every ~500ms

**Serial Output**:
```
[OBSTACLE] 140.2 cm - DETECTED
[OBSTACLE] 80.5 cm - DETECTED
[OBSTACLE] 30.1 cm - DETECTED
```

---

### 5. Disconnect/Reconnect Test (1 minute)

1. **Disconnect** in nRF Connect
   - Expected Serial Output:
     ```
     [BLE] Disconnected
     [BLE] Restarting advertising
     ```

2. **Reconnect**
   - Should receive hello packet again
   - Heartbeat timer resets
   - Obstacle packets resume

---

## Troubleshooting

### No Serial Output
- **Check**: Baud rate set to 115200
- **Check**: Correct COM port selected
- **Fix**: Press EN button on ESP32 to reboot

### "Invalid reading" constantly
- **Cause**: Wiring issue or no object in range
- **Check**: TRIG → GPIO 18, ECHO → GPIO 19
- **Check**: HC-SR04 powered (VCC → 5V, GND → GND)
- **Check**: Object within 2-400cm range

### Distance readings way off
- **Cause**: Voltage divider incorrect or missing
- **Check**: ECHO voltage at GPIO 19 should be ~3.3V (use multimeter)
- **Check**: Resistor values (10kΩ + 20kΩ)

### LED not working
- **Check**: LED orientation (long leg to GPIO 23, short leg to resistor)
- **Check**: 220Ω resistor connected to GND
- **Check**: LED not burned out (test with another LED)

### Can't find "DIYA_CANE_DEV"
- **Check**: ESP32 powered and not resetting
- **Check**: BLE enabled on phone
- **Check**: Not already connected to another device
- **Fix**: Reboot ESP32 (press EN button)

### No BLE packets
- **Check**: Notifications enabled on characteristic `1b050003`
- **Check**: Serial Monitor shows `[BLE] Connected`
- **Check**: Not using TX characteristic (wrong one!)

### Button not working
- **Check**: BOOT button is GPIO 0
- **Check**: Button packet only sent when connected via BLE
- **Check**: Press firmly (should reset ESP32 if held during boot)

---

## Quick Reference

### Serial Log Prefixes
```
[INIT]      - Startup messages
[BLE]       - Connection events
[HELLO]     - Handshake packet sent
[HEARTBEAT] - Periodic heartbeat sent
[US]        - Ultrasonic readings
[OBSTACLE]  - Obstacle detection (when detected=true)
[BUTTON]    - Button press events
```

### BLE Characteristics
```
Service:     1b050001-c852-4752-b883-fa4c0342ab01
TX (Write):  1b050002-c852-4752-b883-fa4c0342ab01
RX (Notify): 1b050003-c852-4752-b883-fa4c0342ab01
```

### Packet Types
```json
// Hello (on connect)
{"v":1,"t":"hello","protocol":1,"firmware":"1.0.0"}

// Heartbeat (every 5s)
{"v":1,"t":"heartbeat"}

// Obstacle (every 500ms when connected)
{"v":1,"t":"obstacle","distance_cm":42.1,"detected":true}

// Button (on press)
{"v":1,"t":"button","button":1,"press":"single"}
```

### LED Patterns
```
DANGER   (0-50cm):    ████████████████  (Solid ON)
WARNING  (50-100cm):  ▓▓░░▓▓░░▓▓░░▓▓░░  (Fast blink 200ms)
CAUTION  (100-150cm): ▓▓▓░░░▓▓▓░░░▓▓▓░  (Slow blink 500ms)
CLEAR    (>150cm):    ░░░░░░░░░░░░░░░░  (OFF)
```

---

## Success Criteria

### ✅ Basic Functionality
- [ ] Serial output at 115200 baud
- [ ] Ultrasonic readings update ~10Hz
- [ ] LED responds to distance changes
- [ ] BLE advertising visible

### ✅ BLE Protocol
- [ ] Can connect from nRF Connect
- [ ] Hello packet received on connect
- [ ] Heartbeat every 5 seconds
- [ ] Obstacle packets every 500ms
- [ ] Button packet on press

### ✅ Obstacle Detection
- [ ] `detected=true` when distance ≤ 150cm
- [ ] `detected=false` when distance > 150cm
- [ ] Distance values match Serial Monitor
- [ ] LED pattern matches distance

### ✅ Robustness
- [ ] Can disconnect and reconnect
- [ ] Advertising restarts after disconnect
- [ ] No crashes or resets
- [ ] Handles invalid ultrasonic readings

---

## Next Steps

**After successful testing**:
1. Integrate with Flutter app
2. Verify obstacle packets received in Flutter
3. Test with `ObstacleIngressService`
4. Verify UI updates with obstacle telemetry

**For production**:
1. Add voltage divider for ECHO pin
2. Replace LED with vibration motor
3. Add proper enclosure
4. Test with real cane mounting

---

**Questions?** Check `FIRMWARE_INTEGRATION_REPORT.md` for detailed documentation.

