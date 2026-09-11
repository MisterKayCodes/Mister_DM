import sys
import os
sys.path.append(os.path.abspath("."))
import asyncio
import httpx
import config

async def test_active_models():
    api_key = config.GROQ_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    test_models = [
        "groq/compound-mini",
        "groq/compound",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-20b"
    ]

    print("=== Testing Lead Triage Completions across Active Groq Models ===")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for model in test_models:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a lead classifier for a Telegram DM campaign. Classify into ONE word: RELATIONAL, TRANSACTIONAL, or DEAD."},
                    {"role": "user", "content": "User: Hey man, loved your video! Do you have a VIP signal group?\nBot: Thanks! Yes we do."}
                ],
                "max_tokens": 10,
                "temperature": 0.0
            }
            try:
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    verdict = res.json()["choices"][0]["message"]["content"].strip()
                    print(f"[SUCCESS] Model: '{model}' --> Verdict: '{verdict}'")
                else:
                    print(f"[FAILED] Model: '{model}' --> Status {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"[ERROR] Model: '{model}' --> Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_active_models())
