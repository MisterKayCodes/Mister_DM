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
