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

### 🧠 Brain — `core/` (Future — Phase 6+)
**Job:** Orchestrate long-running processes. The Scheduler lives here.

The Brain will coordinate the Campaign Scheduler — picking targets, selecting templates
at random, sending DMs via Telethon, tracking results, and managing campaign state transitions.

**Phase 5 Decision:** The Scheduler (`SchedulerService`) is placed in `services/` for now,
not `core/`, because it still coordinates Service calls and follows the same session boundary
rules as other services. It will be promoted to `core/` in a future phase when a true
orchestration layer with independent lifecycle management is warranted.

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
| Missing `StateFilter(None)` or `StateFilter("*")` on root handlers | Handlers without filters will steal input during active FSM flows, breaking wizards. |
| Using `parse_mode="Markdown"` on user data | Telegram's MarkdownV1 parser treats underscores as italics. Usernames crash the parser. Use HTML. |
| Presentation loop logic (e.g. `next(...)`) in Mouth | The Mouth shouldn't know how to query data or handle missing nested relationships. Services provide clean, bounded DTOs. |
| Two-step UI rendering after mutations | If a handler calls `delete()` then manually calls `get_list()` to render, the UI is out of sync. Actions must return a single atomic signal containing the fresh data. |
| Inline import inside a handler or callback function | Delays module loading to runtime — import errors become invisible until the exact button is tapped. All imports must live at the top of the file so failures are caught at startup. |
| Business rule evaluated inside the Mouth (e.g. `if campaign.status != "draft"`) | The handler is making a workflow decision. If the rule changes, every handler that copies the check must be updated. Move the rule into a Service method (e.g. `verify_campaign_modifiable`) that returns a boolean verdict. |
| Service pre-building HTML presentation strings | Services must be format-agnostic. If a Service builds a Telegram HTML string, it cannot be reused for logs, exports, or other channels. Services return raw data objects or dicts; the Mouth renders them. |
| Duplicate UI string blocks across multiple handlers | If the same "Managing Campaign:" summary block is built in 3 handlers separately, any formatting change requires 3 edits. Centralise repeated layout strings in a Service method or a Mouth helper function. |
| Calling a handler function from inside another handler | Creates tight coupling. If the called handler changes its signature, every caller breaks silently. Use atomic Service returns or inline the logic directly. |
| Synchronous file decoding in handlers (e.g. `file.read()`) | Blocks the main asyncio event loop, freezing the bot for all concurrent users if the file is large. Pass bytes to Services and decode inside `asyncio.to_thread()`. |
| Exposing raw ORM entities to the Mouth | If a Service returns a raw SQLAlchemy model to a handler, the handler might trigger lazy-loads outside the session, causing `DetachedInstanceError`. It also binds the UI directly to the DB schema. Services must map models to plain Python dictionaries (or pure DTOs) before returning. |
| Over-eager memory loading (`selectinload` on index lists) | Pulling massive arrays of child models (e.g. templates) while fetching a bulk parent index list introduces severe memory thrashing. Keep relational loads strictly scoped inside single-entity fetches (e.g., `get_by_id`). |
| Loading entire ORM models into RAM before deleting | Inefficient network usage. Execute clean bulk SQL deletion using `session.execute(delete(Model).where(...))` for single-trip atomic deletion. |
| Row-by-row `session.add()` + `flush()` loop | Thrashes connection pools, drops cache, and introduces severe latency blocks. Parse to unique dicts and execute atomic batch plugins (e.g., `sqlite_insert(Model).values(...).on_conflict_do_nothing()`). |
| Hardcoding assumed post-action status in the Mouth | After a scheduler control action (start/pause/stop), the handler must NOT assume the resulting status string. It must unpack the actual DB-verified status returned by the Service and pass that to any keyboard or UI builder. Assumed status creates split-brain UI states where the keyboard shows wrong controls. |
| Inconsistent tuple arity on multi-path returns | If a function signature returns `tuple[bool, str, str]`, every single exit path must return exactly 3 elements. A 2-tuple on any branch will cause a `ValueError` unpack crash at runtime the moment that code path is hit. Use a lint rule or runtime type-check to enforce this. |
| Ghost campaign state on bot restart | If a campaign is marked `running` in the DB and the bot restarts, no asyncio task exists for it. The DB lies. On every bot startup, query all `running` campaigns and revert them to `paused` to restore a truthful state before accepting any user input. |


---

## Code Comment Standards

Use short, brief comment tags to explain architectural decisions and logic. 
Do not use verbose formatting (like `#FIXED` or multi-line blocks) because it occupies too much space in the code. Keep it short but informative.

### The "Why" Comment Standard
Comments explain the pain, not the code. The code already explains itself.

```python
# ❌ Wrong — describes what, not why:
# Opens the database session

# ✅ Right — describes the pain:
# #FIXED: Without a single session, two queries could see different data.
# WHAT WOULD HAPPEN: A write between them makes counts mismatch. Wrong numbers = wrong UI.
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

---

## AI Execution Discipline (The 3-Step Guardrail)

When an AI is in "execution mode" (rapidly generating code), it tends to optimize for "getting it to work" rather than strict architectural compliance. This leads to regression into common bad patterns (like repositories committing transactions). 

To prevent this, the AI must enforce the following discipline on itself:

1. **Pre-flight Declaration (Before writing a file):**
   - The AI must explicitly declare the layer and the applicable rules before generating the file. 
   - *Example:* "Layer: Repository. Rules that apply: No commits, no business logic, returns ORM only."
   - *Why:* Forces the AI to retrieve the constraints into active context *before* the first token of code is generated.

2. **File Header Layer Comment:**
   - Every file must have a 1-3 line comment at the top declaring its layer constraints.
   - *Example:* `# LAYER: Repository — no commits, no rollbacks, no business logic`
   - *Why:* Makes violations visually obvious to human reviewers and reminds the AI of the constraints when re-reading the file during future edits.

3. **Phase Boundary Self-Audit:**
   - Before handing a completed phase back to the human for testing, the AI must run a self-audit checklist:
     - *Do any repos commit?*
     - *Do any services return raw ORM objects?*
     - *Do any handlers call other handlers?*
     - *Do any repos contain if/else business decisions?*
     - *Are all DTOs consistent?*
   - *Why:* Catches inevitable generation mistakes before they waste the human's testing time.

