
import os


def _load_ids(variable_name: str) -> set[int]:
    """Load trusted Discord user IDs from a comma-separated environment variable."""
    raw = os.getenv(variable_name, "")
    result = set()

    for item in raw.split(","):
        item = item.strip()

        if item.isdigit():
            result.add(int(item))

    return result


def is_developer(user_id: int) -> bool:
    """Only explicitly configured developer IDs receive developer access."""
    return user_id in _load_ids("VEYRA_DEVELOPER_IDS")


def is_server_admin(member, guild=None) -> bool:
    """Check server owner or Administrator/Manage Server permission."""
    import discord

    if not isinstance(member, discord.Member):
        return False

    if guild is not None and member.guild.id != guild.id:
        return False

    return (
        member.id == member.guild.owner_id
        or member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
    )
