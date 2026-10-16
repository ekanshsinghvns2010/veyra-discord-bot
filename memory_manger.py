
import json
import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = DATA_DIR / "memory.json"

# Keep only a small window of recent messages in active context.
MAX_RECENT_MESSAGES = 15

DEFAULT_MEMORY = {
    "summary": "",
    "preferences": {},
    "history": [],
}


def _load_all():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORY_FILE.exists():
        return {}

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {MEMORY_FILE}: {error}"
        ) from error


def _save_all(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        dir=DATA_DIR,
        prefix="memory_",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

        os.replace(temp_name, MEMORY_FILE)

    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def _user_key(guild_id, user_id):
    # Separate each person's memory in each server.
    return f"{guild_id}:{user_id}"


def get_user_memory(guild_id, user_id):
    data = _load_all()
    key = _user_key(guild_id, user_id)

    memory = data.get(key, {})

    result = {
        **DEFAULT_MEMORY,
        **memory,
    }

    result["preferences"] = dict(result.get("preferences", {}))
    result["history"] = list(result.get("history", []))

    return result


def get_recent_history(guild_id, user_id):
    memory = get_user_memory(guild_id, user_id)
    return memory["history"][-MAX_RECENT_MESSAGES:]


def add_message(guild_id, user_id, role, content):
    """Store one recent message and return older messages to summarize."""
    if role not in {"user", "assistant"}:
        raise ValueError("Role must be 'user' or 'assistant'.")

    if not isinstance(content, str) or not content.strip():
        return []

    data = _load_all()
    key = _user_key(guild_id, user_id)

    memory = {
        **DEFAULT_MEMORY,
        **data.get(key, {}),
    }

    history = list(memory.get("history", []))
    history.append({
        "role": role,
        "content": content.strip(),
    })

    overflow = []

    if len(history) > MAX_RECENT_MESSAGES:
        overflow = history[:-MAX_RECENT_MESSAGES]
        history = history[-MAX_RECENT_MESSAGES:]

    memory["history"] = history
    data[key] = memory
    _save_all(data)

    return overflow


def update_summary(guild_id, user_id, summary):
    """Save a compact AI-generated summary of useful context."""
    data = _load_all()
    key = _user_key(guild_id, user_id)

    memory = {
        **DEFAULT_MEMORY,
        **data.get(key, {}),
    }

    memory["summary"] = str(summary).strip()[:3000]
    data[key] = memory
    _save_all(data)


def set_preference(guild_id, user_id, name, value):
    """Save a user preference, such as their preferred language."""
    if not name or not isinstance(value, str):
        return

    data = _load_all()
    key = _user_key(guild_id, user_id)

    memory = {
        **DEFAULT_MEMORY,
        **data.get(key, {}),
    }

    preferences = dict(memory.get("preferences", {}))
    preferences[name.strip().lower()] = value.strip()[:300]
    memory["preferences"] = preferences

    data[key] = memory
    _save_all(data)


def clear_user_memory(guild_id, user_id):
    """Delete one user's memory in one server."""
    data = _load_all()
    key = _user_key(guild_id, user_id)

    if key not in data:
        return False

    del data[key]
    _save_all(data)
    return True
