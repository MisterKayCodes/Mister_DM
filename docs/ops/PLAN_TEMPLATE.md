# PLAN TEMPLATE
# Use this structure for every phase plan and every violation report in this project.
# Consistency means the architect and engineer can read any plan and know exactly where to look.
# Saved in docs/ops/ because this is a process document — how we work, not what we're building.

---

# [Phase X — Name] OR [Phase X.Y — Violation Report]

One paragraph. What is the problem this plan solves? What will be true when it's done?

---

## Done Criteria

- [ ] Specific, testable outcome 1
- [ ] Specific, testable outcome 2
- [ ] Tested manually end-to-end

---

## Open Questions For Review

> [!IMPORTANT]
> Any decision that requires the architect or engineer to choose between options.
> Never start building until open questions are resolved.

> [!WARNING]
> Any breaking changes or high-risk decisions.

> [!NOTE]
> Background context that helps the reviewer understand a decision.

---

## Proposed Changes

Group by layer (Memory → Nerves → Mouth). Dependencies first.

### 💾 Memory Layer — `data/`

#### [NEW] [filename](file:///absolute/path)
What this file does and why it exists.

#### [MODIFY] [filename](file:///absolute/path)
What changes and why.

#### [DELETE] [filename](file:///absolute/path)
Why this file is being removed.

---

### ⚡ Nerves Layer — `services/`

#### [NEW] [filename](file:///absolute/path)

---

### 🗣 Mouth Layer — `bot/`

#### [MODIFY] [filename](file:///absolute/path)

---

## Violations Report (for Phase X.5 reviews)

| ID | Severity | File | Line(s) | Rule Broken |
|---|---|---|---|---|
| V-01 | 🔴 Critical | | | |
| V-02 | 🟡 Medium | | | |
| V-03 | 🟢 Minor | | | |

Severity guide:
- 🔴 Critical — will cause a crash or data corruption
- 🟡 Medium — will cause a crash under specific user input (e.g. underscores in names)
- 🟢 Minor — incorrect pattern that will compound into a bigger problem later

---

## Verification Plan

### Manual Verification
Step-by-step test script the user follows in the Telegram bot.
Be specific: "Tap X, expect Y."

---

## My Recommendation

> [!IMPORTANT]
> The architect's verdict. What to do, why, and what to debate before writing code.
