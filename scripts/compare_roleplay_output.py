import sys
import os
sys.path.append(os.path.abspath("."))
import asyncio
import httpx
import config
from core.prompt_builder import build_roleplay_prompt

async def compare_models():
    api_key = getattr(config, "GROQ_API_KEY", "")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    persona = {
        "name": "Elena",
        "core_identity": "You are Elena Chen, executive partner at a luxury private mining firm. Highly intelligent, dry, secretive, high-status.",
        "traits_json": '["private", "dry humor", "high status"]',
        "dark_triad_json": '{"machiavellianism": {"level": "high", "notes": "Never reveal intent directly."}}',
        "rules_json": '["Never say you are an AI", "Keep messages under 25 words"]',
        "quotes_json": '["Hardware moves slow, people move slower.", "I don\'t do advice on Telegram."]'
    }

    system_prompt = build_roleplay_prompt(
        persona=persona,
        contact_name="Alex",
        intel=[{"category": "finances", "key": "crypto_portfolio", "value": "holds 5 BTC"}],
        week=1,
        arc_theme="Managing a private shipment of ASIC miners out of Austin."
    )

    json_system_prompt = (
        system_prompt + "\n\n"
        "### OUTPUT FORMAT REQUIREMENT ###\n"
        "You MUST output your response as a valid JSON object ONLY.\n"
        "JSON Schema:\n"
        "{\n"
        '  "intent": "Explain strategy.",\n'
        '  "confidence_score": 85,\n'
        '  "needs_human": false,\n'
        '  "message": "Your actual text message response."\n'
        "}"
    )

    user_msg = "Hey Elena, saw your post. Do you think I should sell my BTC right now or buy more mining gear?"

    models_to_test = [
        "groq/compound-mini",
        "groq/compound",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile",
        "llama3-70b-8192"
    ]

    print("=== Testing Real Roleplay Quality Across Available Groq Models ===")

    async with httpx.AsyncClient(timeout=20.0) as client:
        for model in models_to_test:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.7,
                "max_tokens": 200
            }
            try:
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                print(f"\n--------------------------------------------------")
                print(f"MODEL: {model} (Status: {res.status_code})")
                if res.status_code == 200:
                    out = res.json()["choices"][0]["message"]["content"].strip()
                    print(f"OUTPUT:\n{out}")
                else:
                    print(f"ERROR ({res.status_code}): {res.text[:150]}")
            except Exception as e:
                print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    asyncio.run(compare_models())
