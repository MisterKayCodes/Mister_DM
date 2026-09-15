import sys
import os
sys.path.append(os.path.abspath("."))
import asyncio
import httpx
import config

async def check_quota():
    api_key = getattr(config, "GROQ_API_KEY", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"=== Checking Groq Quota Headers for Key ({api_key[:10]}...) ===")

    payload = {
        "model": "groq/compound-mini",
        "messages": [
            {"role": "user", "content": "ping"}
        ],
        "max_tokens": 5
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            print(f"Status Code: {res.status_code}")
            print("\n--- Rate Limit Headers ---")
            for k, v in sorted(res.headers.items()):
                if "ratelimit" in k.lower() or "retry" in k.lower():
                    print(f"{k}: {v}")
            
            if res.status_code == 200:
                print("\n--- Usage Data ---")
                print(res.json().get("usage", {}))
            else:
                print(f"Error output: {res.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_quota())
