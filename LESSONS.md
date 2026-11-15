# Mister_DM — Lessons Learned

<!--
Format:
## [Short title describing the issue]
- Problem: [What broke and what the symptom was]
- Solution: [What fixed it]
- Rule: [What to always do or never do in the future]
- Verified by: [Exact human observation that proved it worked]
-->

## Circular Imports & Stale Barrel Exporter Imports During Domain Refactor
- Problem: Moving services into domain subpackages (`services/leads/`, `services/campaigns/`) caused `ImportError` circular loops during startup and `ModuleNotFoundError` across handlers due to stale flat imports (`services.account_service`). Static AST checks (`py_compile`) passed because AST only checks syntax, not runtime import execution.
- Solution: Updated all internal sibling imports inside domain subpackages to direct file imports (`from services.leads.relationship_service import RelationshipService`), updated all 17 handler/api files to domain package exports, and validated locally via `py -c "import main"`.
- Rule: 1. Inside a domain subpackage (`services/leads/`), NEVER import siblings via the parent package barrel (`from services.leads import X`); import direct files or defer imports inside methods.
  2. After any structural refactor, run `py -c "import main"` to test actual module execution, not just AST compilation.
- Verified by: VPS log showed `INFO: Application startup complete`, `Uvicorn running on 0.0.0.0:8013`, and `INFO:aiogram.event:Update is handled` with zero errors.

## Aiogram edit_text Keyboard Type Mismatch (ReplyKeyboardMarkup in edit_text)
- Problem: Passing `reply_markup=main_menu_keyboard()` (which returns a `ReplyKeyboardMarkup`) to `status_msg.edit_text()` caused `pydantic_core.ValidationError` (`Input should be a valid dictionary or instance of InlineKeyboardMarkup`). The bot crashed mid-action and left the user frozen on "Scouting in progress...".
- Solution: Removed `reply_markup` from all `edit_text` error calls; sent bottom menu keyboards via a separate `message.answer()` call.
- Rule: `edit_text()` and `edit_caption()` in aiogram ONLY accept `InlineKeyboardMarkup` or `None`. Persistent bottom menu buttons (`ReplyKeyboardMarkup`) must always be sent as new messages via `message.answer()`.
- Verified by: Bot successfully edited the "Scouting in progress..." status bubble into results without crashing or getting frozen.

## Private Telegram /c/ Links Entity Resolution Failure
- Problem: Telethon's `client.get_entity()` throws `Cannot find any entity` when passed internal browser links like `https://t.me/c/3577283817/1` because Telethon expects integer peer channel IDs, not web path strings.
- Solution: Added URL parser to `_resolve_entity_with_cache()` in `scout_mixin.py` that extracts the digit string after `/c/` and converts it to integer `-100<id>` before resolving.
- Rule: Always parse Telegram private message links (`/c/<id>/`) to integer channel IDs (`int(f"-100{id}")`) before calling `get_entity()`.
- Verified by: VPS log confirmed `🔍 Resolved private chat link 'https://t.me/c/3577283817/1' to Channel ID: -1003577283817` and successfully fetched 100 messages.

## In-Memory FSM State Loss on Multi-Turn Button Navigation
- Problem: Storing extracted leads solely in FSM `state.update_data()` caused "Session expired. Please scout again" errors when users navigated menus before tapping "Create Campaign with Leads", wiping the lead list.
- Solution: Backed FSM storage with a module-level user cache dictionary (`USER_SCOUT_CACHE[user_id]`) so scouted data persists across state resets.
- Rule: Any burst-extracted external data that users act on across multiple screens must be cached by `user_id` outside transient FSM state.
- Verified by: User tapped "Create Campaign with Leads", entered campaign name "UK betting", and bot auto-loaded 13 scouted leads with zero rescrapes.
