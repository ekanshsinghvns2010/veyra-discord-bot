
import json
import os
import tempfile

DATA_DIR = "data"
MODES_FILE = os.path.join(DATA_DIR, "modes.json")

VALID_MODES = {"chat", "longchat"}


def _load_modes():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(MODES_FILE):
        return {}

    try:
        with open(MODES_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except (json.JSONDecodeError, OSError):
        print("Warning: Could not read modes.json. Using default modes.")
        return {}


def _save_modes(modes):
    os.makedirs(DATA_DIR, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=DATA_DIR,
        prefix="modes_",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(modes, file, indent=2)

        os.replace(temp_path, MODES_FILE)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def get_chat_mode(guild_id):
    modes = _load_modes()
    mode = modes.get(str(guild_id), "chat")

    return mode if mode in VALID_MODES else "chat"


def set_chat_mode(guild_id, mode):
    if mode not in VALID_MODES:
        raise ValueError("Mode must be 'chat' or 'longchat'.")

    modes = _load_modes()
    modes[str(guild_id)] = mode
    _save_modes(modes)
