# DEMO CHECKLIST - Quick Start

**Branch**: `hotfix/demo-flutter-gemini-direct`  
**Time**: 5 minutes to run  
**Status**: ✅ READY

---

## Pre-Demo Setup (5 minutes)

### ✅ Step 1: Confirm Branch
```bash
git branch --show-current
# Must show: hotfix/demo-flutter-gemini-direct
```

### ✅ Step 2: Start Flutter App
```bash
cd apps/flutter
flutter run
```

**Wait for**: App to load on device/emulator

---

## Demo Flow (Live)

### 1️⃣ Show the App
- Open 2ndEye app
- Show home screen
- Explain: "Assistive AI for visually impaired users"

### 2️⃣ Demonstrate Assist Feature
- **Press the Assist button**
- **Take a photo** (point at something interesting)
- **Wait 2-3 seconds**
- **Listen to TTS speak the description**

### 3️⃣ Key Points to Highlight
- ✅ "Analyzes images in real-time"
- ✅ "Describes scene for visually impaired users"
- ✅ "Detects hazards and objects"
- ✅ "Works with phone camera or smart goggles"

### 4️⃣ Optional: Show Multiple Examples
- Indoor scene (furniture, doors)
- Outdoor scene (cars, people, signs)
- Text/signs (will read visible text)

---

## If Something Goes Wrong

### App crashes?
```bash
# Restart
flutter run
```

### No TTS sound?
- Check device volume
- Check TTS is enabled in device settings
- Try again with different image

### "Network error"?
- Check internet connection
- Verify API key in code (should be there)
- Check Gemini API quota

### Still stuck?
```bash
# Quick rebuild
flutter clean
flutter pub get
flutter run
```

---

## Post-Demo

### Save Demo Branch
```bash
# Branch is saved, just switch back to main
git checkout main
```

### Clean Up (Later)
```bash
# When Docker networking is fixed:
git checkout main
git branch -D hotfix/demo-flutter-gemini-direct
# Then revert assist_api.dart to use backend
```

---

## What the Audience Will See

1. **User presses Assist** 📸
2. **Camera opens** 📷
3. **Takes photo** ✨
4. **Processing indicator** ⏳ (2-3 sec)
5. **TTS speaks description** 🔊
6. **Success!** ✅

---

## Emergency Contacts

- **API Key Issues**: Check `apps/flutter/lib/features/assist/infrastructure/gemini_direct.dart`
- **Flutter Issues**: `flutter doctor`
- **Build Issues**: `flutter clean && flutter pub get`

---

## Success Indicators

✅ App loads without crashes  
✅ Assist button is visible  
✅ Camera opens when pressed  
✅ Image captured successfully  
✅ TTS speaks within 5 seconds  
✅ Description makes sense  

---

**You're ready! Good luck with the demo! 🚀**

**Current time budget**: 
- Setup: 5 min
- Demo: 5-10 min  
- Q&A: 5 min
- **Total: ~20 min**

---

## Quick Test Now (Recommended)

```bash
# 1. Make sure you're on the right branch
git branch --show-current

# 2. Run the app
cd apps/flutter
flutter run

# 3. Test Assist once
# - Press Assist
# - Take photo
# - Hear TTS

# If it works ✅ YOU'RE READY!
```
