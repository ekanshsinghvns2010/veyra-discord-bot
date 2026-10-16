
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODES_FILE = DATA_DIR / "modes.json"

VALID_MODES = {"chat", "longchat"}


def _load_modes() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not MODES_FILE.exists():
        return {}

    try:
        with MODES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise RuntimeError("modes.json must contain a JSON object.")

        return data

    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {MODES_FILE}: {error}"
        ) from error


def _save_modes(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = MODES_FILE.with_suffix(".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        temp_path.replace(MODES_FILE)

    finally:
        if temp_path.exists():
            temp_path.unlink()


def get_chat_mode(guild_id: int) -> str:
    modes = _load_modes()
    mode = modes.get(str(guild_id), "chat")

    return mode if mode in VALID_MODES else "chat"


def set_chat_mode(guild_id: int, mode: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError("Mode must be 'chat' or 'longchat'.")

    modes = _load_modes()
    modes[str(guild_id)] = mode
    _save_modes(modes)

    print(f"Saved Veyra mode settings to {MODES_FILE}")
