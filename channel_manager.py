
import json
from pathlib import Path

DATA_DIR = Path("data")
CONFIG_PATH = DATA_DIR / "channels.json"


def _load_channels() -> dict:
    """Load the saved AI chat channels for all servers."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except FileNotFoundError:
        return {}

    except json.JSONDecodeError:
        raise RuntimeError(
            "channels.json contains invalid JSON. "
            "Fix the file before starting Veyra."
        )


def _save_channels(data: dict) -> None:
    """Save channel settings safely."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = CONFIG_PATH.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temp_path.replace(CONFIG_PATH)


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
    """
    Compatibility helper for existing bot.py.
    Returns all configured channel IDs as a set.
    """
    return get_chat_channels(guild_id)


def set_chat_channel(guild_id: int, channel_id: int) -> None:
    """Add one AI chat channel without replacing existing channels."""
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


def remove_chat_channel(guild_id: int, channel_id: int) -> bool:
    """Remove only the specified AI chat channel."""
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
    return True
