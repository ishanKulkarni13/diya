# 🔑 PASTE YOUR API KEY HERE

## Quick Steps:

### 1. Open this file:
```
apps/flutter/.env
```

### 2. Find this line:
```env
GEMINI_API_KEY=your-api-key-here
```

### 3. Replace with your key:
```env
GEMINI_API_KEY=AIzaSyD...paste-your-actual-key-here
```

### 4. Save the file

### 5. Run Flutter:
```bash
cd apps/flutter
flutter run
```

---

## ✅ Your Key is Safe

- **`.env` file is git ignored** - Won't be committed
- **Verify**: Run `git status` and you should NOT see `apps/flutter/.env`
- **Test**: `git check-ignore apps/flutter/.env` should output the filename

---

## Get Your API Key

**Website**: https://aistudio.google.com/app/apikey

1. Sign in with Google
2. Click "Create API Key"
3. Copy the key (starts with `AIzaSy...`)
4. Paste in `apps/flutter/.env`

---

## That's It!

✅ **Safe**: Key won't be committed  
✅ **Simple**: Just paste and run  
✅ **Secure**: Using environment variables  

---

**Full documentation**: See `DEMO_API_KEY_SETUP.md` for more details.
