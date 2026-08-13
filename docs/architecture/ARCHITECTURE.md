This is the Master Anatomy. By treating your code as a living organism, you ensure that every file has a biological purpose. If a part starts doing someone else's job, the system becomes a "mutant" that is hard to maintain and prone to "cancerous" bugs.

🧬 The Anatomy of a Senior System: Mister Alert
🧠 The Brain (core/)
Biological Role: Cognition, Math, and Decisions.
Simple Note: This is where the "Why" and "How much" live. It takes numbers and returns answers. It is Pure—meaning if you give it the same numbers, it always gives the same answer.
Files: core/trades/tracker.py, core/alerts/engine.py, core/calculators/
⛔ THE BRAIN WARNINGS: * If you see import sqlalchemy or from data...: STOP. The Brain should not have to "remember" anything itself; it just processes what it's told.
If you see import asyncio or await: STOP. Thinking should be instant (synchronous). Let the Nervous System handle the timing.
If you see import aiogram: STOP. The Brain doesn't have a mouth. It doesn't know Telegram exists.
🧬 The Nervous System (services/)
Biological Role: Synapses, Signaling, and Orchestration.
Simple Note: The "Middleman." It takes a signal from the Eyes, carries it to the Brain, and then carries the Brain's decision to the Hands or Mouth.
Files: services/event_bus.py, services/trade_engine.py
⛔ THE NERVOUS SYSTEM WARNINGS:
If you see complex if/else trading logic: STOP. The Nervous System is a messenger, not a decider. Move that logic to the Brain.
If you see import aiogram: STOP. The Nervous System shouldn't care how the message is "spoken," only that a message needs to be sent.
💾 The Memory (data/)
Biological Role: Long-term storage and DNA.
Simple Note: The "Vault." It ensures that if the organism "dies" (crashes), it can be reborn with all its previous knowledge intact.
Files: data/models.py, data/repository.py, data/database.py
⛔ THE MEMORY WARNINGS:
If you see import core.alerts.engine: STOP. The Vault shouldn't care how the Brain thinks. It only stores the data the Brain used.
If you see print() or logging of user messages: STOP. The Memory is for data, not for "chatting."
👄 The Mouth & Ears (bot/)
Biological Role: Social Interaction and UI.
Simple Note: The "Interface." It translates human language (Telegram buttons) into system signals and vice-versa.
Files: bot/routers/, bot/keyboards/, bot/notification_handler.py
⛔ THE MOUTH/EARS WARNINGS:
If you see price calculation math: STOP. The Mouth shouldn't calculate pips. It should ask the Brain for the answer and just "say" it.
If you see session.execute(select(...)): STOP. The Mouth doesn't reach into the Vault. It asks the Repository (Memory) for the data.
👁️ The Eyes & 🖐️ The Hands (providers/ & integrations/)
Biological Role: Perception and Action.
Simple Note: The "Sensors." They watch the outside world (Binance, CoinGecko) and report back.
Files: services/price_providers/, services/exchanges/
⛔ THE EYES/HANDS WARNINGS:
If you see Trade objects or User objects: STOP. The Eyes only see prices and symbols. They don't need to know who the user is.
If you see bot.send_message: STOP. The Eyes don't talk to the user. They just report what they see to the Nervous System.
🦴 The Skeleton (main.py / bootstrap.py)
Biological Role: Structure and Birth.
Simple Note: The "Frame." It defines the order in which the body is built and ensures all parts are connected.
Files: main.py, config.py
⛔ THE SKELETON WARNINGS:
If you see business logic here: STOP. The Skeleton just holds things up; it doesn't think.
If it gets too large: STOP. Move wiring to a container.py or dispatcher.py. The Skeleton should stay lean.
🚨 Immediate "System Failure" Checklist
If any of these occur, you are violating the Mister Alert Organism design:

Circular Dependency: Does core import services while services imports core? System Paralysis.
Logic Leakage: Is there a Decimal calculation happening inside a Telegram Router? Brain Hemorrhage.
IO in Core: Is the Brain waiting for a URL or a Database? Brain Freeze.
Direct DB access in Bot: Is the Mouth digging through the Vault? Safety Breach.
