# MISTER.md — AI Instructions for Working With Kay

> **This document is written FOR the AI assistant working on this project.**
> Read this before touching any files. These are not suggestions — they are the rules.

---

## What Is Mister (Kay)?

Mister is a local terminal tool already installed on this machine.
It is available as the `kay` command from anywhere in the terminal.
Its job: handle file operations, search, bundling, and diagnostics — **so the AI doesn't have to**.

Every time the AI reads a file with a tool call instead of using `kay`, it wastes tokens.
Every time the AI calls `list_dir` instead of `kay scan`, it wastes tokens.
Every time the AI reads 5 files separately instead of running `kay bundle`, it wastes tokens.

**The rule is simple: if Kay can do it, Kay does it.**

---

## Kay Location

```
Executable : C:\Kaycris\MY_PROJECTS\Mister\kay.bat
PATH entry : C:\Kaycris\MY_PROJECTS\Mister
```

If `kay` is not found in a terminal session, prepend this to the current session:
```powershell
$env:PATH += ";C:\Kaycris\MY_PROJECTS\Mister"
```

---

## Full Command Reference

### `kay scan [path]`
Shows the full folder tree of a directory.

```powershell
kay scan                          # scan current folder
kay scan C:\path\to\project       # scan a specific path
kay scan --folders-only           # show only directories
kay scan --depth 2                # limit depth
kay scan --line-count             # show file sizes
```

**AI uses this instead of:** `list_dir` tool calls.

---

### `kay read <file> [range]`
Read a file's contents with optional line numbers and ranges.

```powershell
kay read bot.py                   # read full file
kay read bot.py --lines           # with line numbers
kay read bot.py 10-50             # only lines 10 to 50
kay read bot.py 10-50 --lines     # range with line numbers
```

**AI uses this instead of:** `view_file` tool calls.

---

### `kay bundle <file1> <file2> ... or <folder>`
**THE MOST IMPORTANT COMMAND FOR TOKEN SAVING.**

Combines multiple files (or entire folders) into a single output string.
The AI runs this once and gets all file contents in one shot.

```powershell
kay bundle data/models data/repositories     # bundle two folders
kay bundle bot.py core/config.py main.py     # bundle specific files
kay bundle bot/                              # bundle entire folder
```

**AI uses this instead of:** reading files one by one with multiple `view_file` calls.
**Token savings:** Up to 70% reduction on multi-file reads.

---

### `kay find <term> [options]`
Search across all files in the current project.

```powershell
kay find "session_path"             # find text in all files
kay find "import" --ext .py         # filter by extension
kay find "TODO" --ignore-case       # case-insensitive
kay find "def send" --context 3     # show 3 lines of context
kay find "FloodWait" --count        # only show match counts
```

**AI uses this instead of:** `grep_search` tool calls.

---

### `kay imports`
Scans all Python files and reports broken/missing imports.

```powershell
kay imports
```

**AI runs this after writing new Python files** to confirm no import errors before continuing.

---

### `kay check`
Full project health check — syntax errors, missing dependencies, heavy files.

```powershell
kay check
```

**AI runs this after completing a phase** before committing.

---

### `kay listen`
Shows the last crash error in a clean, readable format.
Works when the project is run with `kay_run` which captures crashes automatically.

```powershell
kay_run python main.py   # run with crash capture
kay listen               # view the last crash
```

**AI uses this instead of:** hunting through log files or asking the user to paste errors.

---

### `kay todo`
Find all `TODO`, `FIXME`, and `BUG` comments across the codebase.

```powershell
kay todo
```

**AI runs this** to audit what's unfinished before declaring a phase complete.

---

### `kay analyze <file>`
Maps a file's classes, functions, and dependencies — without reading the full file content.

```powershell
kay analyze data/models/account.py
```

**AI uses this** to understand a file's structure cheaply before deciding whether to read the full file.

---

### `kay detect [path]`
Zero-token local refactor scanner. Detects code smells, oversized files, duplicate patterns.
No API calls. Runs entirely locally.

```powershell
kay detect .              # scan entire current project
kay detect bot/handlers   # scan specific folder
```

---

### `kay locate <name>`
Fuzzy-find a project folder anywhere inside `C:\Kaycris\` — ignores case, spaces, underscores.

```powershell
kay locate mister_dm
kay locate telethon client
```

---

### `kay copy <file>` / `kay paste [file]`
Copy file to clipboard, paste clipboard to file (with auto-backup).

```powershell
kay copy bot.py             # copy to clipboard
kay paste newfile.py        # paste clipboard to file
kay paste --preview         # preview before pasting
kay paste --undo            # undo last paste
```

---

### `kay clean --backups`
Delete all `.bak` backup files recursively.

```powershell
kay clean --backups --dry-run    # preview first
kay clean --backups              # delete
```

---

### `kay extract <file> <name> <output>`
Safely extract a class or function into a new file without breaking brackets.

```powershell
kay extract bot.py MyClass new_module.py
```

---

### `kay barrel <folder>`
Auto-generate an `__init__.py` or `index.js` export barrel for a folder.

```powershell
kay barrel bot/handlers
```

---

### `kay teach`
Teach Kay new command synonyms for the `kay talk` natural language interface.

---

### `kay usage`
View Groq API token usage dashboard (when using AI-powered commands).

---

## The AI Workflow Rules

### Rule 1 — Scan First, Ask Never
At the start of any session or task, run `kay scan` to understand the project structure.
Never ask the user "what does the project look like?"

### Rule 2 — Bundle, Don't Read One By One
When multiple files are needed, always `kay bundle` them in one shot.
Never chain multiple `view_file` or `read_file` calls for different files.

### Rule 3 — Listen Before Guessing
When there's a crash or error, run `kay listen` before forming any hypothesis.
Never guess what the error is without seeing it.

### Rule 4 — Check Imports After Every Write
After writing any new Python file or modifying imports, run `kay imports`.
A broken import that isn't caught immediately can waste the entire next session.

### Rule 5 — Detect Before Refactoring
Before suggesting refactors, run `kay detect` on the target folder.
Let the tool identify the real problems. Don't guess.

### Rule 6 — Health Check Before Every Commit
Before any `git commit`, run `kay check` to confirm the project is healthy.

---

## Session Start Checklist (For AI)

Every time a new session begins on this project:

```powershell
# 1. Confirm kay is available
kay scan

# 2. Get project state
kay bundle docs/ROADMAP.md docs/SCHEMA.md docs/MVP_LOCK.md

# 3. Check current phase from ROADMAP.md
# 4. Continue from where we left off
```

That's three commands. Zero file-reading tool calls. Full context in seconds.
