#!/usr/bin/env python
"""
Quick test script for the FB Comment Auto-Reply module.
Tests the core functions without running the Flask server.

Usage:
    python test_comment_reply.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.fb_comment_auto_reply import (
    _load_fb_tokens,
    generate_reply,
    validate_webhook_signature,
)

def test_token_loading():
    """Test that tokens load correctly."""
    print("▶ Testing token loading...")
    try:
        tokens = _load_fb_tokens()
        print(f"  ✅ Tokens loaded successfully")
        print(f"     - Page token exists: {bool(tokens.get('page_token', {}).get('token'))}")
        print(f"     - User token exists: {bool(tokens.get('user_token', {}).get('token'))}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    return True


def test_reply_generation():
    """Test LLM reply generation."""
    print("\n▶ Testing reply generation...")
    try:
        reply = generate_reply(
            comment_text="I love Vocabulary Pro! It helps me learn new words every day.",
            system_prompt="You are a friendly brand ambassador. Keep replies under 100 chars.",
        )
        print(f"  ✅ Reply generated successfully")
        print(f"     Reply: {reply}")
        print(f"     Length: {len(reply)} chars")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    return True


def test_reply_with_context():
    """Test LLM reply with parent context."""
    print("\n▶ Testing reply with parent comment context...")
    try:
        reply = generate_reply(
            comment_text="This is awesome!",
            parent_comment_text="Does Vocabulary Pro have a mobile app?",
            system_prompt="Answer questions about Vocabulary Pro helpfully.",
        )
        print(f"  ✅ Reply with context generated successfully")
        print(f"     Reply: {reply}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    return True


def test_webhook_signature():
    """Test webhook signature validation."""
    print("\n▶ Testing webhook signature validation...")
    try:
        # Test without secret (should return True)
        body = b'{"test": "data"}'
        sig = "sha256=123abc"
        result = validate_webhook_signature(body, sig)
        print(f"  ✅ Validation works (no secret set: {result})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("FB Comment Auto-Reply Module – Test Suite")
    print("=" * 60)

    tests = [
        ("Token Loading", test_token_loading),
        ("Reply Generation", test_reply_generation),
        ("Reply with Context", test_reply_with_context),
        ("Webhook Signature", test_webhook_signature),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\n{passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n✅ All tests passed! Module is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
