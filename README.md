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
- Track reply status per target
- Tag pain points from conversations
- Export conversations for analysis

## What It Does NOT Do

- ❌ AI replies
- ❌ Auto classification
- ❌ Lead scoring
- ❌ Scraping
- ❌ Multi-tenant / SaaS
- ❌ Billing / Permissions

---

## Architecture

This project follows the **Biological Anatomy** pattern.
See `docs/architecture.md` for the full breakdown.

| Layer | Folder | Role |
|---|---|---|
| 🧠 Brain | `core/` | Pure business logic |
| 🧬 Nervous System | `services/` | Orchestration |
| 💾 Memory | `data/` | Database / Storage |
| 👄 Mouth & Ears | `bot/` | Telegram UI (aiogram) |
| 👁️ Eyes & Hands | `telethon_client/` | Outreach sender |
| 🦴 Skeleton | `main.py` | Entry point |

---

## Stack

- **Python 3.11+**
- **aiogram 3** — Control panel bot
- **Telethon** — User-client outreach sender
- **SQLite** — Local database
- **SQLAlchemy** — ORM

---

## Setup

```bash
# 1. Clone
git clone <repo>
cd mister_dm

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your tokens

# 5. Run
python main.py
```

---

## Build Phases

- [x] Phase 0: Project foundation (git, structure, DB schema)
- [ ] Phase 1: Accounts (add / list / delete)
- [ ] Phase 2: Campaigns (create / list)
- [ ] Phase 3: Templates (add / list / delete)
- [ ] Phase 4: Import Targets
- [ ] Phase 5: Scheduler (send messages with delays)
- [ ] Phase 6: Reply tracking
- [ ] Phase 7: Pain Point tagging
- [ ] Phase 8: Export conversations
