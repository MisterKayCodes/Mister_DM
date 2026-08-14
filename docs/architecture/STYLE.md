# KAY CODE STYLE GUIDE
# A living document. Every rule here exists because of a real decision made on a real project.
# When a new pattern is established, it gets written here so every future project follows it.

---

## 1. Project Tooling — Always Use `mister` (kay)

Every project that Kay works on uses the `kay` CLI tool for file operations.

- `kay scan` instead of `list_dir`
- `kay bundle` instead of reading files one by one
- `kay check` before every commit
- `kay imports` after every new Python file

**Rule:** If `kay` can do it, `kay` does it. Calling file-reading tools when `kay` is available wastes tokens.

---

## 2. Code Comments — Explain The Pain, Not The Code

Comments must answer **WHY**, not **WHAT**.

The code already says what it does. The comment must explain the reasoning,
the architectural decision, or the pain that would happen without it.

### ❌ NEVER write this:
```python
# This function returns the count of targets
async def get_target_count(...):
```

### ✅ ALWAYS write this:
```python
# We use SELECT COUNT(*) here instead of loading all targets into memory (len(session.targets)).
# With 50,000 targets, len() would pull every single row into RAM just to count them.
# COUNT(*) returns a single integer and never touches the actual row data.
async def get_target_count(...):
```

---

## 3. Bug/Fix Documentation — The `#FIXED:` Tag

Every time a bug is fixed or a filter/handler is corrected, document it
immediately above the fixed code using this exact format:

```python
# #FIXED: Short description of what was wrong.
# WHAT WOULD HAVE HAPPENED: Explain the exact crash or bug that would have occurred
# without this fix, so future maintainers understand the risk.
```

**Why this exists:** In a Telegram bot with dozens of message filters, a single
wrong filter can silently steal messages from the wrong handler and crash in
non-obvious ways. The `#FIXED` tag creates a permanent audit trail.

---

## 4. Never Store Derived Data

**Rule:** If a value can be calculated from existing rows, NEVER store it as a column.

```python
# ❌ NEVER DO THIS:
campaign.targets_count = 245

# ✅ DO THIS:
count = await get_target_count(session, campaign_id)
```

**Why:** Stored counts become wrong the moment a delete or bulk-wipe runs
and you forget to decrement the counter. Derived counts are always correct because
they are calculated fresh from the source of truth every time.

---

## 5. Never Load Data You Don't Need

**Rule:** Only load the columns and rows you actually need.

```python
# ❌ NEVER DO THIS (loads every row into memory just to count):
targets = await session.execute(select(Target).where(...))
count = len(targets.scalars().all())

# ✅ DO THIS (returns a single integer, zero memory overhead):
count = await session.execute(select(func.count()).where(Target.campaign_id == id))
```

---

## 6. Status-Gated Mutations

**Rule:** Any operation that modifies campaign data (add targets, delete templates, etc.)
must first check that the campaign status is `draft`.

```python
if campaign.status != "draft":
    await message.answer("Cannot modify a running or completed campaign.")
    return
```

**Why:** The Phase 5 Scheduler picks targets and sends messages in real-time.
If you allow targets to be added or removed while the scheduler is running, you
introduce race conditions where the scheduler might skip or double-send.

---

## 7. Database-Level Constraints Over Application-Level Checks

**Rule:** Uniqueness and integrity must be enforced at the database level, not in Python.

```python
# ✅ The database enforces this, not our code:
__table_args__ = (UniqueConstraint('campaign_id', 'username'),)
```

**Why:** Application-level checks have a race condition. Two simultaneous requests
can both pass the Python check and both attempt to insert, causing duplicates.
The database constraint is atomic and cannot be raced.

---

## 8. View Limits — Preview + File Pattern

**Rule:** When displaying a list of items that could be very long (targets, templates, etc.),
never render the entire list in a single Telegram message.

- Show the first **20** items inline.
- If the count exceeds 20, automatically generate and send a `.txt` file with the full list.

```python
# We deliberately cap the inline preview at 20.
# Telegram messages have a hard 4096 character limit.
# Pagination is over-engineering for an MVP and adds UI complexity with zero business value.
# The real solution at scale is an export file, which gives the user more value anyway
# (they can open it in Excel, search it, share it, etc.).
```

---

## 9. Bulk Operations Over Row-By-Row

**Rule:** When inserting or deleting many rows, use bulk operations.

```python
# ✅ Bulk delete (one SQL statement):
await session.execute(delete(Target).where(Target.campaign_id == campaign_id))

# ❌ Never loop and delete one by one:
for target in targets:
    await session.delete(target)
```

**Why:** Row-by-row operations inside a loop make N database round trips.
A bulk operation makes 1 round trip regardless of dataset size.

---

## 10. Unique Button Prefixes — Prevent Router Collisions

**Rule:** Every delete/confirm button in every handler must use a unique prefix
that identifies which entity it belongs to.

| Entity   | Delete Button           | Confirm Button                  |
|----------|-------------------------|---------------------------------|
| Account  | `🗑 Delete Acc {id}`   | `✅ Yes, Delete Acc {id}`       |
| Campaign | `🗑 Delete Camp {id}`  | `✅ Yes, Delete Camp {id}`      |
| Template | `🗑 Delete Tpl {id}`   | `✅ Yes, Delete Tpl {id}`       |
| Target   | `🗑 Clear Targets`     | `✅ Yes, Clear Targets`         |

**Why:** aiogram's `F.text.startswith()` filter is greedy. If two handlers share
the same prefix (e.g. both use `🗑 Delete `), one router will intercept
the other's messages, try to parse the wrong ID, and crash.

---

## 11. Telegram Message Parse Mode — Always Use HTML, Never Raw Markdown

**Rule:** Never use `parse_mode="Markdown"` (MarkdownV1) on messages that contain user-generated content.

**The crash this rule prevents:**
```
aiogram.exceptions.TelegramBadRequest:
Bad Request: can't parse entities: Can't find end of the entity starting at byte offset 165
```

**Why it happens:** Telegram's MarkdownV1 parser treats underscores as italic markers.
A username like `john_doe` opens an italic span that never closes — instant crash.
MarkdownV2 fixes this but requires escaping 18+ special characters, which is fragile.

**The rule:**
```python
# ❌ NEVER use raw Markdown when the string contains user data:
await message.answer(f"Target: {username}", parse_mode="Markdown")

# ✅ Use HTML mode + safe_html() from utils/telegram_utils.py:
from utils.telegram_utils import safe_html
await message.answer(f"Target: {safe_html(username)}", parse_mode="HTML")

# ✅ Or omit parse_mode entirely for plain text lists (no formatting needed):
await message.answer(f"1. {username}\n2. {username2}")
```

**What `safe_html()` does:** Escapes only `&`, `<`, `>` — the three characters HTML cares about.
These almost never appear in Telegram usernames or campaign names, making it the safest choice.

**Location:** `utils/telegram_utils.py` also contains `bold()`, `italic()`, and `code()` helpers
for all HTML-formatted output so you never have to write raw HTML tags in handler code.

---

## 12. Centralize UI Strings in Constants

**Rule:** Handlers must never contain hardcoded UI strings (prompts, errors, success messages). All UI strings must be extracted to `bot/constants/messages.py`.

```python
# ❌ NEVER DO THIS (Hardcoded strings scattered in logic):
await message.answer("What is the name of this campaign?")

# ✅ ALWAYS DO THIS (Strings imported from constants):
from bot.constants.messages import CAMP_ASK_NAME
await message.answer(CAMP_ASK_NAME)
```

**Why:**
1. **Separation of Concerns:** The Mouth's job is UI coordination. The exact text is presentation data.
2. **Readability:** Handlers become much shorter and easier to read when long string blocks are removed.
3. **Consistency:** If 3 handlers need to say "Campaign not found", they all use the exact same string (`CAMP_NOT_FOUND`). If we want to change it to "⚠️ Campaign not found", we change it in one place.

