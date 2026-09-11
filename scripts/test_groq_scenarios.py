import sys
import os
sys.path.append(os.path.abspath("."))
import asyncio
import httpx
import config

async def test_scenarios():
    api_key = config.GROQ_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    model = "groq/compound-mini"

    scenarios = [
        ("Relational Test", "User: Hey bro! I saw your post on Telegram. Hope you are having a blessed week!\nBot: Hey thanks man! Appreciate it."),
        ("Transactional Test", "User: How much does the signal bot cost per month? Can I pay with USDT?\nBot: Hey, check out our packages."),
        ("Dead Test", "User: Stop spamming me you scruffy scammer block me immediately\nBot: Sorry about that.")
    ]

    print(f"=== Testing Groq Live Model '{model}' across Triage Scenarios ===")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for name, chat in scenarios:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a lead classifier for a Telegram DM campaign. Output ONLY ONE WORD: RELATIONAL, TRANSACTIONAL, or DEAD."},
                    {"role": "user", "content": chat}
                ],
                "max_tokens": 10,
                "temperature": 0.0
            }
            res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            if res.status_code == 200:
                verdict = res.json()["choices"][0]["message"]["content"].strip()
                print(f"[{name}] Verdict: '{verdict}'")
            else:
                print(f"[{name}] ERROR status {res.status_code}")

if __name__ == "__main__":
    asyncio.run(test_scenarios())
