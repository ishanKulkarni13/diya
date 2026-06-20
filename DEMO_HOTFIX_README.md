# DEMO HOTFIX: Direct Gemini Call from Flutter

**Branch**: `hotfix/demo-flutter-gemini-direct`  
**Status**: READY FOR DEMO  
**Created**: 2026-06-20 for urgent demo

---

## What This Does

**Bypasses the broken Docker backend** and calls Gemini API directly from Flutter.

### Changes Made

1. ✅ Added `google_generative_ai` package to Flutter
2. ✅ Created `GeminiDirect` service for direct API calls
3. ✅ Patched `AssistApi` to use direct call instead of backend
4. ✅ Keeps original backend code commented out for easy revert

---

## How to Run

### 1. Build and Run Flutter App

```bash
cd apps/flutter
flutter run
```

### 2. Test Assist Feature

1. Open app
2. Press **Assist button**
3. Take a photo or select from gallery
4. **Gemini will analyze directly from Flutter**
5. TTS will speak the result

---

## What Works

✅ **Assist button** → Captures image  
✅ **Direct Gemini API call** → Analyzes image  
✅ **TTS** → Speaks result  
✅ **No backend needed** → Bypasses Docker issue

---

## What This Breaks (Temporarily)

❌ **Session management** - No backend session tracking  
❌ **Metrics/logging** - No backend analytics  
❌ **Auth integration** - Direct call doesn't use user auth  
❌ **Backend features** - TTS generation, complex intent handling

**These are acceptable for DEMO purposes.**

---

## Revert After Demo

### Option 1: Delete Branch

```bash
git checkout main
git branch -D hotfix/demo-flutter-gemini-direct
```

### Option 2: Keep for Reference

```bash
git checkout main
# Branch stays for reference
```

### Option 3: Fix Backend & Remove Hotfix

Once Docker networking is fixed:

```dart
// In assist_api.dart, uncomment original code
// Delete gemini_direct.dart
// Remove google_generative_ai package
```

---

## Files Modified

```
apps/flutter/pubspec.yaml                                    # Added google_generative_ai
apps/flutter/lib/features/assist/infrastructure/gemini_direct.dart   # NEW - Direct API call
apps/flutter/lib/features/assist/infrastructure/assist_api.dart      # PATCHED - Use direct call
```

---

## API Key Note

**⚠️ API KEY IS HARDCODED FOR DEMO**

Current key in `gemini_direct.dart`:
```dart
static const String _apiKey = 'AIzaSyDiRr1R6IuJXcx9-1raPbQPNQ3XBHy2ZA8';
```

**For production:**
1. Move to environment variables
2. Use backend proxy (original architecture)
3. Never commit API keys

---

## Quick Test

```bash
# 1. Switch to hotfix branch (if not already)
git checkout hotfix/demo-flutter-gemini-direct

# 2. Run Flutter
cd apps/flutter
flutter run

# 3. In app: Press Assist → Take photo → Listen to TTS
```

---

## Troubleshooting

### "Package not found"
```bash
cd apps/flutter
flutter pub get
```

### "API Key invalid"
Check the key in `gemini_direct.dart` is correct

### "Still calling backend"
Make sure you're on the hotfix branch:
```bash
git branch --show-current
# Should show: hotfix/demo-flutter-gemini-direct
```

---

## Commit Log

```
2d60ffb hotfix(demo): call Gemini directly from Flutter - bypass Docker network issue
```

---

**This is a TEMPORARY HOTFIX for demo purposes. Do NOT use in production.**

Good luck with the demo! 🚀
