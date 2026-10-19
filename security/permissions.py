
import os
import discord


def _load_ids(variable_name: str) -> set[int]:
    """Read comma-separated Discord IDs from environment variables."""
    raw = os.getenv(variable_name, "")
    ids = set()

    for item in raw.split(","):
        item = item.strip()
        if item.isdigit():
            ids.add(int(item))

    return ids


def is_developer(user_id: int) -> bool:
    """Only explicitly allowlisted users count as Veyra developers."""
    return user_id in _load_ids("VEYRA_DEVELOPER_IDS")


def is_server_admin(member, guild=None) -> bool:
    """Check whether a member owns or administers this server."""
    if not isinstance(member, discord.Member):
        return False

    if guild is not None and member.guild.id != guild.id:
        return False

    permissions = member.guild_permissions

    return (
        member.id == member.guild.owner_id
        or permissions.administrator
        or permissions.manage_guild
    )
