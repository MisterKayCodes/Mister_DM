# SCHEMA
# Final database design. Lock before writing models.
# Database: SQLite. ORM: SQLAlchemy.

---

## Entities & Relationships

```
accounts
    └─< campaigns
            └─< templates
            └─< targets
                    └─< target_pain_tags >─ pain_tags
```

---

## accounts

| Column       | Type     | Notes                          |
|--------------|----------|-------------------------------|
| id           | INTEGER  | Primary key, auto-increment   |
| name         | TEXT     | e.g. "Forex Outreach Account" |
| session_path | TEXT     | Path to .session file         |
| delay_min    | INTEGER  | Minimum delay in minutes      |
| delay_max    | INTEGER  | Maximum delay in minutes      |
| is_active    | BOOLEAN  | Default: True                 |
| created_at   | DATETIME | Auto-set on creation          |

---

## campaigns

| Column     | Type     | Notes                                       |
|------------|----------|---------------------------------------------|
| id         | INTEGER  | Primary key                                 |
| name       | TEXT     | e.g. "Forex Outreach August"                |
| account_id | INTEGER  | FK → accounts.id                           |
| status     | TEXT     | draft / running / paused / completed / stopped |
| created_at | DATETIME | Auto-set on creation                        |

**Status flow:**
```
draft → running → paused → running → completed
                         ↘ stopped
```

---

## templates

| Column      | Type     | Notes                    |
|-------------|----------|--------------------------|
| id          | INTEGER  | Primary key              |
| campaign_id | INTEGER  | FK → campaigns.id       |
| content     | TEXT     | The message body         |
| created_at  | DATETIME | Auto-set on creation     |

> Belong to one campaign only. No global library in V1.
> System picks one at random when sending.

---

## targets

| Column      | Type     | Notes                              |
|-------------|----------|------------------------------------|
| id          | INTEGER  | Primary key                        |
| campaign_id | INTEGER  | FK → campaigns.id                 |
| username    | TEXT     | Telegram username (no @)           |
| status      | TEXT     | pending / sent / failed / replied  |
| note        | TEXT     | Free-text note. One field. V1.     |
| sent_at     | DATETIME | Null until sent                    |
| replied_at  | DATETIME | Null until reply detected          |

**Status flow:**
```
pending → sent → replied
        ↘ failed
```

---

## pain_tags

| Column     | Type     | Notes                      |
|------------|----------|----------------------------|
| id         | INTEGER  | Primary key                |
| name       | TEXT     | Unique. e.g. "Manual Posting" |
| created_at | DATETIME | Auto-set on creation       |

> Created once. Reused forever.
> Count = count of target_pain_tags rows for this tag.

---

## target_pain_tags *(junction table)*

| Column      | Type    | Notes                      |
|-------------|---------|----------------------------|
| id          | INTEGER | Primary key                |
| target_id   | INTEGER | FK → targets.id           |
| pain_tag_id | INTEGER | FK → pain_tags.id         |

> A target can have multiple pain tags.
> A pain tag can be assigned to multiple targets.
> This is how we count: `SELECT COUNT(*) WHERE pain_tag_id = X`

---

## What We Do NOT Store

| Data               | Reason                              |
|--------------------|-------------------------------------|
| Message history    | Telegram owns this. Telethon reads it live on export. |
| Conversation logs  | Same as above.                      |
| Reply content      | Too complex for V1. Telegram UI handles it. |

---

## Key Rules

1. Never access DB directly from `bot/` — go through `data/repositories/`
2. Never put Telegram logic in `data/` — that belongs in `telethon_client/`
3. `pain_tags.name` must be UNIQUE — no duplicates, no dirty data
4. `targets.username` should be stored WITHOUT the `@` symbol
