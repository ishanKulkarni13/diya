#!/usr/bin/env python3
"""
Test Gemini multimodal with a known good image.

This script tests the Gemini provider independently of FastAPI,
allowing us to verify that multimodal image analysis works
regardless of the web framework.

Usage:
    python scripts/test_multimodal.py path/to/test/image.jpg
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.assist.providers.gemini import GeminiProvider
from app.config.settings import settings


async def test_with_file(image_path: Path):
    """Test Gemini multimodal with an image file."""
    
    if not image_path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return False
    
    # Load image
    print(f"\n📁 Loading image: {image_path}")
    image_bytes = image_path.read_bytes()
    
    print(f"   Size: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.2f} KB)")
    print(f"   JPEG magic valid: {image_bytes.startswith(b'\\xff\\xd8')}")
    print(f"   First 16 bytes: {image_bytes[:16].hex()}")
    
    if not image_bytes.startswith(b'\xff\xd8'):
        print(f"   ⚠️  Warning: File doesn't have JPEG magic bytes (ff d8)")
    
    # Check API key
    api_key = settings.providers.gemini_api_key
    if not api_key:
        print(f"\n❌ Error: GEMINI_API_KEY not configured")
        print(f"   Set it in .env or environment variables")
        return False
    
    print(f"\n🔑 Using API key: {api_key[:10]}...")
    print(f"📦 Using model: {settings.providers.gemini_model_name}")
    
    # Create provider
    print(f"\n🚀 Creating Gemini provider...")
    provider = GeminiProvider(
        api_key=api_key,
        model_name=settings.providers.gemini_model_name
    )
    
    # Test multimodal analysis
    print(f"\n🔍 Analyzing image with Gemini...")
    try:
        result = await provider.analyze_image(
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            intent_type="describe_scene"
        )
        
        print(f"\n✅ Success!")
        print(f"\n📝 Analysis Result:")
        print(f"   Provider: {result.provider_name}")
        print(f"   Model: {result.model_name}")
        print(f"   Latency: {result.latency_ms}ms")
        print(f"\n💬 Spoken Text:")
        print(f"   {result.analysis.spoken_text}")
        print(f"\n📄 Display Text:")
        print(f"   {result.analysis.display_text}")
        print(f"\n⚠️  Hazards: {result.analysis.hazards or 'None detected'}")
        print(f"🔍 Detected Objects: {result.analysis.detected_objects or 'None'}")
        print(f"📊 Confidence: {result.analysis.confidence}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_invalid_data():
    """Test Gemini with invalid data to verify error handling."""
    print(f"\n🧪 Testing with invalid data...")
    
    api_key = settings.providers.gemini_api_key
    if not api_key:
        print(f"❌ Skipping: API key not configured")
        return False
    
    provider = GeminiProvider(
        api_key=api_key,
        model_name=settings.providers.gemini_model_name
    )
    
    # Test 1: Empty bytes
    print(f"\n   Test 1: Empty bytes")
    try:
        await provider.analyze_image(
            image_bytes=b"",
            mime_type="image/jpeg",
            intent_type="describe_scene"
        )
        print(f"   ❌ Should have failed but didn't")
        return False
    except Exception as e:
        print(f"   ✅ Correctly rejected: {type(e).__name__}")
    
    # Test 2: Invalid JPEG
    print(f"\n   Test 2: Invalid JPEG bytes")
    try:
        await provider.analyze_image(
            image_bytes=b"123",
            mime_type="image/jpeg",
            intent_type="describe_scene"
        )
        print(f"   ❌ Should have failed but didn't")
        return False
    except Exception as e:
        print(f"   ✅ Correctly rejected: {type(e).__name__}")
    
    print(f"\n✅ Error handling works correctly")
    return True


async def main():
    """Main entry point."""
    print("=" * 70)
    print("🧪 Gemini Multimodal Test Script")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("\n📖 Usage: python scripts/test_multimodal.py path/to/image.jpg")
        print("\n🔍 Available test modes:")
        print("   1. With image file: python scripts/test_multimodal.py image.jpg")
        print("   2. Error handling test: python scripts/test_multimodal.py --test-errors")
        sys.exit(1)
    
    if sys.argv[1] == "--test-errors":
        success = await test_with_invalid_data()
    else:
        image_path = Path(sys.argv[1])
        success = await test_with_file(image_path)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed")
    print("=" * 70 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
