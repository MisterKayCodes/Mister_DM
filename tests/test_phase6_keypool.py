import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from providers.groq_pool import GroqPool

def run_test():
    print("🚀 Starting Phase 6 Groq API Key Pool Verification Test...")

    # 1. Test single-key behavior
    single_pool = GroqPool(["gsk_single_key_1234"])
    k1 = single_pool.get_next_key()
    k2 = single_pool.get_next_key()
    assert k1 == "gsk_single_key_1234"
    assert k2 == "gsk_single_key_1234"
    print("✅ Single key pool test passed!")

    # 2. Test multi-key round-robin rotation
    multi_pool = GroqPool(["gsk_key_A_1111", "gsk_key_B_2222", "gsk_key_C_3333"])
    k_a = multi_pool.get_next_key()
    k_b = multi_pool.get_next_key()
    k_c = multi_pool.get_next_key()
    k_a2 = multi_pool.get_next_key()

    assert k_a == "gsk_key_A_1111"
    assert k_b == "gsk_key_B_2222"
    assert k_c == "gsk_key_C_3333"
    assert k_a2 == "gsk_key_A_1111"
    print("✅ Multi-key round-robin rotation test passed!")

    # 3. Test rate limit cooldown tracking
    print("⚡ Marking Key A as cooling (simulating 429 rate limit)...")
    multi_pool.mark_cooling("gsk_key_A_1111", cooldown_seconds=60)

    # Key A should now be skipped, returning B then C then B again
    next1 = multi_pool.get_next_key()
    next2 = multi_pool.get_next_key()
    next3 = multi_pool.get_next_key()

    assert next1 == "gsk_key_B_2222"
    assert next2 == "gsk_key_C_3333"
    assert next3 == "gsk_key_B_2222"
    assert "gsk_key_A_1111" not in (next1, next2, next3)
    print("✅ Key cooldown auto-bypass test passed!")

    print("\n🎉 Phase 6 Verification Test Passed 100%!")

if __name__ == "__main__":
    run_test()
