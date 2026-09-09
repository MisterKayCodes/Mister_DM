import asyncio
from clients.simulator_client import simulator_client
import config

async def test_simulator_client():
    print("=== Testing Phase 2: Simulator Integration Client ===")
    print("Simulator API URL:", config.SIMULATOR_API_URL)
    
    # 1. Health Check Test
    print("\n1. Testing Simulator Health Check...")
    is_healthy = await simulator_client.check_health()
    print("Simulator Health Result:", "ONLINE" if is_healthy else "OFFLINE (Expected if Simulator is not running locally)")
    
    # 2. Structure & Exception Validation Test
    print("\n2. Testing BaseClient Headers & Config...")
    assert simulator_client.base_url == "http://localhost:8012"
    assert simulator_client.api_key == config.SIMULATOR_API_KEY
    assert simulator_client.service_name == "Mister Simulator"
    print("--> Config & Header validation PASSED!")

    print("\n=== PHASE 2 SIMULATOR CLIENT VERIFICATION PASSED ===")

if __name__ == "__main__":
    asyncio.run(test_simulator_client())
