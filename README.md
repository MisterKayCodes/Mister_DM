# Mister DM

A personal Telegram outreach tool for market discovery.

**Purpose:**
Find Forex/Crypto educators on Telegram, start conversations, discover pain points, track patterns, and decide what to build.

This is NOT a sales bot. NOT a CRM. NOT an AI platform.

It is a **market discovery engine**.

---

## What It Does

- Manage multiple Telegram accounts for outreach
- Create campaigns with message templates
- Import target usernames (paste or TXT upload)
- Send messages with randomized human-like delays
- Track reply status per target (pending → sent → replied / failed / skipped)
- Tag pain points from conversations
- Add notes per target
- Export full conversations as text files
- View analytics dashboard (reply rates, failure rates, daily usage)
- Global blacklist — users who opt out are never contacted again across any campaign
- Per-account daily send limits — automatically pauses campaigns when limit is reached

## What It Does NOT Do

- ❌ AI replies
- ❌ Auto classification
- ❌ Lead scoring
- ❌ Scraping
- ❌ Multi-tenant / SaaS
- ❌ Billing / Permissions

---

## Architecture

This project follows the **Biological Anatomy** pattern:

| Layer | Folder | Role |
|---|---|---|
| 🧠 Brain | `core/` | Long-running processes (Scheduler, ReplyListener) |
| 🧬 Nervous System | `services/` | Business logic, session ownership |
| 💾 Memory | `data/` | Models, repositories — pure SQL, no logic |
| 👄 Mouth & Ears | `bot/` | Telegram UI (aiogram handlers, keyboards, states) |
| 👁️ Eyes & Hands | `services/telethon_client.py` | Outreach sender |
| 🦴 Skeleton | `main.py` | Entry point |

Full rules: `docs/architecture/ROLES_AND_RULES.md`

---

## Stack

- **Python 3.11+**
- **aiogram 3** — Control panel bot
- **Telethon** — User-client outreach sender
- **SQLite** — Local database (single file, no server needed)
- **SQLAlchemy (async)** — ORM

---

## Setup

```bash
# 1. Clone
git clone https://github.com/MisterKayCodes/Mister_DM
cd Mister_DM

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Linux / macOS (VPS)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — add BOT_TOKEN, and set DRY_RUN=True for first test

# 5. Run
python main.py
```

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `BOT_TOKEN` | Your Telegram bot token from @BotFather | `123456:ABC...` |
| `DRY_RUN` | If `True`, logs sends without actually sending | `True` |
| `DEV_DELAY_MIN` | Min delay between sends (seconds) | `60` |
| `DEV_DELAY_MAX` | Max delay between sends (seconds) | `120` |

---

## Build Phases — MVP Complete ✅

| Phase | Feature | Status |
|---|---|---|
| 0 | Project foundation (git, structure, DB schema) | ✅ |
| 1 | Accounts (add / list / delete) | ✅ |
| 2 | Campaigns (create / list / delete) | ✅ |
| 3 | Templates (add / list / delete) | ✅ |
| 4 | Import Targets (paste or TXT upload) | ✅ |
| 5 | Scheduler (send with delays, pause/resume/stop) | ✅ |
| 6 | Reply Tracking (Telethon listener) | ✅ |
| 7 | Pain Point Tagging & Notes | ✅ |
| 7.5 | Message Persistence (log all sent/received) | ✅ |
| 8 | Export Conversations (to text file) | ✅ |
| 9 | Analytics Dashboard (reply rate, failure rate) | ✅ |
| 10A | Global Blacklist (opt-out safety gate) | ✅ |
| 10B | Daily Send Limits (per-account, auto-reset) | ✅ |

**MVP is feature-complete. Next step: live testing.**

---

## Project Structure

```
Mister_DM/
├── bot/
│   ├── constants/       # UI strings (messages.py)
│   ├── handlers/        # Mouth — one handler per feature
│   ├── keyboards/       # ReplyKeyboard builders
│   ├── states/          # FSM state definitions
│   └── utils/           # UI layout helpers
├── core/
│   ├── scheduler.py     # Campaign send loop
│   └── reply_listener.py# Telethon reply watcher
├── data/
│   ├── models/          # SQLAlchemy ORM models
│   └── repositories/    # Pure SQL queries
├── docs/
│   ├── architecture/    # ROLES_AND_RULES, STYLE, SCHEMA
│   └── planning/        # ROADMAP, MVP_LOCK, BACKLOG
├── services/            # Business logic, session owners
├── utils/               # Shared helpers
├── main.py              # Entry point
└── config.py            # Environment config
```
