# 🔑 API Key Setup for Demo

**IMPORTANT**: Your API key will NOT be committed to git ✅

---

## Step 1: Add Your API Key

Open the file: `apps/flutter/.env`

```bash
# Navigate to the file
cd apps/flutter
# Open .env in your editor
```

**Find this line:**
```env
GEMINI_API_KEY=your-api-key-here
```

**Replace with your actual key:**
```env
GEMINI_API_KEY=AIzaSyD...your-actual-key-here
```

---

## Step 2: Verify It's Not Tracked by Git

```bash
git status
```

You should **NOT** see `apps/flutter/.env` in the list.

✅ **It's properly ignored by git!**

---

## Where to Get Your API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key
5. Paste it in `apps/flutter/.env`

---

## Safety Features

✅ **`.env` is in `.gitignore`** - Won't be committed  
✅ **Code reads from environment** - No hardcoded keys  
✅ **`.env.example` provided** - For team reference  
✅ **Clear error message** - If key is missing  

---

## How It Works

### Before (❌ Bad - Hardcoded)
```dart
static const String _apiKey = 'AIzaSy...'; // COMMITTED TO GIT!
```

### After (✅ Good - Environment Variable)
```dart
static String get _apiKey {
  final key = dotenv.env['GEMINI_API_KEY'];
  if (key == null || key.trim().isEmpty) {
    throw StateError('GEMINI_API_KEY not found in .env file');
  }
  return key.trim();
}
```

---

## Testing

After adding your key:

```bash
cd apps/flutter
flutter run
```

If the key is missing or invalid, you'll see a clear error:
```
GEMINI_API_KEY not found in .env file.
Please add your API key to apps/flutter/.env
```

---

## For Your Team

When sharing this project:

1. **Share** the `.env.example` file ✅
2. **Don't share** your actual `.env` file ❌
3. **Tell teammates** to copy `.env.example` to `.env`
4. **Each person** adds their own API key

```bash
# Team member setup:
cd apps/flutter
cp .env.example .env
# Then edit .env and add their API key
```

---

## Files Modified

```
apps/flutter/.env                    # YOUR API KEY (git ignored)
apps/flutter/.env.example            # Template for team (committed)
apps/flutter/.gitignore              # Ensures .env is ignored
apps/flutter/lib/.../gemini_direct.dart  # Reads from .env
```

---

## Double-Check Safety

```bash
# This should NOT show apps/flutter/.env
git status

# This should show .env is ignored
git check-ignore apps/flutter/.env
# Expected output: apps/flutter/.env

# Verify your key is there
cat apps/flutter/.env | grep GEMINI_API_KEY
# Should show: GEMINI_API_KEY=AIzaSy...
```

---

**✅ Your API key is safe and will not be committed to git!**
