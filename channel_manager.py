
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "channels.json"


def _load_channels() -> dict:
    """Load saved AI chat channels for all servers."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        return {}

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise RuntimeError("channels.json must contain a JSON object.")

        return data

    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {CONFIG_PATH}: {error}"
        ) from error


def _save_channels(data: dict) -> None:
    """Save channel settings safely."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = CONFIG_PATH.with_suffix(".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        temp_path.replace(CONFIG_PATH)

    finally:
        if temp_path.exists():
            temp_path.unlink()


def get_chat_channels(guild_id: int) -> set[int]:
    """Return all configured AI chat channel IDs for a server."""
    data = _load_channels()
    channel_ids = data.get(str(guild_id), [])

    if not isinstance(channel_ids, list):
        return set()

    return {
        int(channel_id)
        for channel_id in channel_ids
        if str(channel_id).isdigit()
    }


def get_chat_channel(guild_id: int):
    """Compatibility helper for older code."""
    return get_chat_channels(guild_id)


def set_chat_channel(guild_id: int, channel_id: int) -> None:
    """Add one channel without removing other configured channels."""
    data = _load_channels()
    server_id = str(guild_id)
    existing = data.get(server_id, [])

    if not isinstance(existing, list):
        existing = []

    channel_ids = {
        int(item)
        for item in existing
        if str(item).isdigit()
    }

    channel_ids.add(int(channel_id))
    data[server_id] = sorted(channel_ids)
    _save_channels(data)

    print(f"Saved channel configuration to {CONFIG_PATH}")


def remove_chat_channel(guild_id: int, channel_id: int) -> bool:
    """Remove only the specified channel."""
    data = _load_channels()
    server_id = str(guild_id)
    existing = data.get(server_id, [])

    if not isinstance(existing, list):
        existing = []

    channel_ids = {
        int(item)
        for item in existing
        if str(item).isdigit()
    }

    if int(channel_id) not in channel_ids:
        return False

    channel_ids.remove(int(channel_id))

    if channel_ids:
        data[server_id] = sorted(channel_ids)
    else:
        data.pop(server_id, None)

    _save_channels(data)
    print(f"Updated channel configuration at {CONFIG_PATH}")
    return True


def remove_guild_channels(guild_id: int) -> None:
    """Remove all saved channels for a server."""
    data = _load_channels()

    if data.pop(str(guild_id), None) is not None:
        _save_channels(data)
