# ROLES AND RULES
# The Mister DM Organism — Architectural Law
# Version 1.0 | Every rule here was born from a real decision made on a real project.
# Update this file every time a new architectural decision is settled. It compounds over time.

---

## The Organism Model

Mister DM is not a flat script. It is an organism. Every component has one biological role.
Violating the role of a component is an architectural breach. This document defines those roles.

```
┌──────────────────────────────────────────────┐
│                  ORGANISM                     │
│                                              │
│  🗣  Mouth       →  bot/                     │
│  🧠  Brain       →  core/ (future)           │
│  ⚡  Nerves      →  services/ (future)        │
│  💾  Memory      →  data/                    │
│  🔧  Utilities   →  utils/                   │
└──────────────────────────────────────────────┘
```

---

## Role Definitions

### 🗣 Mouth — `bot/`
**Job:** Receive user input. Render output. Nothing else.

The Mouth listens for Telegram messages, validates the shape of user input
(e.g. "is this a button press or free text?"), and decides which action to trigger.
It renders responses back to the user.

**The Mouth is NEVER allowed to:**
- Instantiate `AsyncSessionLocal` or any database session directly.
- Import from `data/repositories/` directly.
- Contain business logic (e.g. "should this campaign be deleted?").
- Perform string transformations that belong in `utils/`.

**The Mouth is ONLY allowed to:**
- Import from `services/` (the Nerves) to trigger business operations.
- Import from `bot/keyboards/` to build UI.
- Import from `bot/states/` to manage FSM state.
- Call `state.get_data()` / `state.update_data()` to pass context between steps.

---

### ⚡ Nerves — `services/`
**Job:** Coordinate business logic. Own the session. Call the repositories.

The Nerves are the intermediary between the Mouth and the Memory.
When a handler needs to "add an account" or "import targets", it calls a Service method.
The Service opens the database session, calls the appropriate repository functions,
handles errors, and returns a clean result to the handler.

**The Nerves are NEVER allowed to:**
- Send Telegram messages (`message.answer()`).
- Know anything about aiogram, FSM, or keyboard layouts.
- Hold state between requests (Services are stateless — one call, one result).

**The Nerves are ONLY allowed to:**
- Open `AsyncSessionLocal` sessions.
- Call `data/repositories/` functions.
- Apply business rules (e.g. "only draft campaigns can be deleted").
- Return simple result objects (`dict`, `tuple`, named result) to the Mouth.

---

### 💾 Memory — `data/`
**Job:** Speak to the database. Nothing else.

The Memory layer has two sub-layers:
- `data/models/` — SQLAlchemy ORM models. Define tables. Define relationships. That is all.
- `data/repositories/` — Pure database operations. SELECT, INSERT, UPDATE, DELETE.

**The Memory is NEVER allowed to:**
- Contain business logic (e.g. "if status is draft, allow delete").
- Import from `bot/`, `services/`, or `utils/` except for pure data helpers.
- Open its own sessions. Sessions are passed in by the caller (the Nerves).

**The Memory is ONLY allowed to:**
- Define ORM models and table constraints.
- Execute database queries using the session passed by the caller.
- Return raw model objects or primitive values (int, str, list).

---

### 🔧 Utilities — `utils/`
**Job:** Pure functions. No state. No imports from any other project layer.

`utils/` contains functions that could theoretically be copy-pasted into any other
project and still work. They have no knowledge of aiogram, SQLAlchemy, or this app.

**Currently contains:**
- `string_utils.py` — `clean_username()`, `generate_safe_filename()`

**The rule:** If a function only takes primitive inputs and returns primitive outputs,
it belongs in `utils/`. If it touches the database, the bot, or external services,
it does not belong here.

---

### 🧠 Brain — `core/` (Future — Phase 5+)
**Job:** Orchestrate long-running processes. The Scheduler lives here.

The Brain will coordinate the Campaign Scheduler — picking targets, selecting templates
at random, sending DMs via Telethon, tracking results, and managing campaign state transitions.

The Brain imports from `services/` to trigger operations. It never speaks to the
database directly and never touches aiogram.

---

## Anti-Patterns (Hard Rules)

| Anti-Pattern | Why It's Banned |
|---|---|
| Handler imports `AsyncSessionLocal` | The Mouth is doing Memory work. Session ownership belongs to the Nerves. |
| Repository opens its own session | The repository must receive the session as a parameter so the caller controls the transaction boundary. |
| `len(model.relationship)` to count rows | Loads all rows into RAM. Use `SELECT COUNT(*)` via `get_X_count()` repo function. |
| Storing derived data as a column (e.g. `targets_count`) | Stored counts become stale. Derived counts are always correct. |
| Button prefix shared between two routers | `F.text.startswith()` is greedy. Shared prefixes cause one router to steal and crash the other's messages. |
| Business logic inside a repository | Repositories are dumb. They execute queries. Services decide whether to call them. |
| Business logic inside a handler | Handlers render UI. Business decisions belong in Services. |

---

## Code Comment Standards

### The `#FIXED:` Tag
Every corrected bug or architectural fix must be documented directly above the fixed code:

```python
# #FIXED: Short description of what was wrong.
# WHAT WOULD HAVE HAPPENED: The exact crash, data corruption, or silent failure
# that would have occurred if this was left unfixed.
```

### The "Why" Comment Standard
Comments explain the pain, not the code. The code already explains itself.

```python
# ❌ Wrong — describes what, not why:
# Opens the database session

# ✅ Right — describes the pain:
# We open a single session for this entire handler so that the template count
# and the target count are read in the same transaction. Two separate sessions
# could theoretically see different data if a write lands between them.
async with AsyncSessionLocal() as session:
```

---

## Folder Structure (Standard — Use On Every Project)

```
project_root/
├── bot/                    # 🗣 Mouth
│   ├── handlers/           # Message listeners and response renderers
│   ├── keyboards/          # Reply keyboard builders
│   └── states/             # FSM state definitions
├── core/                   # 🧠 Brain (scheduler, orchestrators)
├── services/               # ⚡ Nerves (business logic coordinators)
├── data/                   # 💾 Memory
│   ├── models/             # ORM table definitions
│   └── repositories/       # Database query functions
├── utils/                  # 🔧 Utilities (pure functions, no layer deps)
├── docs/
│   ├── architecture/       # ROLES_AND_RULES.md, STYLE.md, SCHEMA.md
│   ├── planning/           # ROADMAP.md, MVP_LOCK.md, BACKLOG.md
│   └── ops/                # MISTER.md (AI workflow rules, kay commands)
├── config.py               # Environment config (stays in root)
└── main.py                 # Entry point (stays in root)
```

This folder structure is the standard for all future Kay projects.
Any new project should begin with this skeleton before writing a single line of logic.

---

## Phase Review Protocol (Phase 4.5 and beyond)

Before graduating from any phase, the architect (user) reviews the code against this document.

1. Architect reads the handlers and identifies suspected violations.
2. Architect states the violation and the rule it breaks.
3. AI agrees or contests with reasoning.
4. If agreed: violation is fixed and this document is updated if a new rule is needed.
5. If contested: architectural debate happens before any code is written.

This is how this document grows. It is never written in one sitting.
It is a record of every hard decision made in production.
