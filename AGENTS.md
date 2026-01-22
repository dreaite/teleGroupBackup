# Agent Development Guidelines - Telegram Group Backup & AI Bot

This document provides essential information for agentic coding agents to operate effectively in this repository.

## 1. Project Overview
This repository contains two primary components:
- **Group Message Backup Tool**: A Telethon-based client that forwards and backs up messages from source groups to target groups, tracking edits and deletions.
- **AI Bot Service**: A plugin-based AI assistant (using `python-telegram-bot`) that integrates with various AI providers (OpenAI, Gemini, Grok, etc.).

## 2. Build, Lint, and Test Commands

### Environment Setup
The project uses a virtual environment located at `/home/dreaife/bot/venv`.
```bash
source /home/dreaife/bot/venv/bin/activate
pip install -r requirements.txt
```

### Running the Services
- **Group Backup Bot**:
  ```bash
  python3 telebot/group_backup_bot.py --config telebot/group_backup_config.yml
  ```
- **AI Test Bot**:
  ```bash
  python3 telebot/dreaife_test_bot.py
  ```

### Testing & Linting
Currently, there is no formal test suite (like pytest) or linter (like ruff) configured.
- **Run single script test**: Simply execute the script with the venv python.
- **Verification**: Manually run the entry point scripts and check logs in `/logs/bot/<bot-name>/`.
- **Unit Testing**: Consider adding a `tests/` directory and using `pytest` for new features.

## 3. Code Style Guidelines

### General Principles
- **Language**: Python 3.12+ (Project runs on 3.12)
- **Concurrency**: Use `asyncio` and `async/await` throughout.
- **Encoding**: Always use UTF-8.
- **Line Length**: Aim for 100-120 characters.

### Imports
Group imports in the following order, separated by a blank line:
1. Standard library imports (e.g., `asyncio`, `logging`).
2. Third-party library imports (e.g., `telethon`, `yaml`, `openai`).
3. Local application/module imports.
Use absolute imports or explicit relative imports (e.g., `from .mapper import MessageMapper`).

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `GroupBackupClient`).
- **Functions/Variables**: `snake_case` (e.g., `handle_new_message`).
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_RETENTION_DAYS`).
- **Private members**: Prefix with a single underscore (e.g., `_parse_config`).

### Types and Documentation
- **Type Hints**: Mandatory for function signatures. Use `typing` module or built-in types (Python 3.10+ style like `list[str] | None`).
- **Docstrings**: Required for classes and public methods. Prefer Google or ReStructuredText style.

### Async/Await
- Use `asyncio.run()` only in the main entry point.
- Avoid blocking calls in async functions; use thread pools if necessary for I/O.
- Properly handle `asyncio.CancelledError` if needed.

### Error Handling
- Use `try...except` blocks around I/O operations and API calls.
- Log errors with `logger.error(..., exc_info=True)` to capture stack traces.
- Don't swallow exceptions silently unless there's a very good reason.

### Logging
- Use the standard `logging` library.
- Log files are typically stored in `/logs/bot/<bot-name>/`.
- Use `TimedRotatingFileHandler` for production logs.
- Use descriptive log messages including relevant IDs (e.g., `chat_id`, `msg_id`).

## 4. Project Structure
- `telebot/`: Contains bot entry points and core logic.
  - `group_backup/`: Core logic for the message backup tool.
  - `ai_sdk/`: AI client wrappers (OpenAI, etc.) shared by bots.
  - `doc/`: User manuals and technical documentation.
- `ai_plugins/`: Plugin architecture for AI providers.
  - `base/`: Base classes for AI integration.
  - `openai/`, `gemini/`, etc.: Provider-specific implementations.
- `deploy/`: Systemd service files for deployment.
- `data/`: Local storage for sessions, mappings, and exports.
- `logs/`: Directory for log files.

## 5. Agent-Specific Instructions
- **Configuration**: Always check `telebot/group_backup_config.yml` (or `.example.yml`) before modifying config-related code.
  - Config defines source groups, targets (1-to-1 or 1-to-many), and topic IDs.
- **Persistence**: 
  - `MessageMapper` stores ID mappings in JSON.
  - Backups are exported as JSONL in `.bak` files.
- **Telethon vs python-telegram-bot**: 
  - `group_backup_bot.py` uses `Telethon` (Client API).
  - `dreaife_test_bot.py` uses `python-telegram-bot` (Bot API).
  - Do NOT mix their patterns.
- **Security**: Never hardcode API keys. Use `.env` and `python-dotenv`.
- **Troubleshooting**:
  - **Login Failed**: If Telethon fails to log in, delete session files in `/data/bot/group_backup/*.session` and restart to re-authenticate.
  - **Logs**: Check `/logs/bot/group_backup/backup.log`.

## 6. Development Workflow
- **Branching**: Develop features in separate branches.
- **Pull Requests**: Submit changes via PR.
- **Verification**:
  1. Modify code.
  2. Run locally to verify: `python3 telebot/group_backup_bot.py ...`
  3. If deploying: `sudo systemctl restart group_backup_bot`

## 7. Example Workflow: Adding Source Link Feature
*Reference for future agents*

### Task
Add a clickable link to the original message in the forwarded message header.

### Steps Taken
1.  **Analysis**:
    -   Identified target file: `telebot/group_backup/handlers.py`.
    -   Found `_build_message_header` and `_process_single_target`.
2.  **Implementation**:
    -   Modified `_process_single_target` to fetch `chat` object safely.
    -   Updated `_build_message_header` to generate links based on public (`t.me/username/id`) or private (`t.me/c/id/id`) chat types.
3.  **Deployment**:
    -   Restarted service: `sudo systemctl restart group_backup_bot`.

---
*Updated by Antigravity Agent - 2026-01-22*
