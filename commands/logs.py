
import os
import json
import asyncio
import discord

from pathlib import Path
from config import PREFIX, DEVELOPMENT_GUILD_ID
from security.permissions import is_server_admin


# ============================================================
# VEYRA LOGGING CONFIGURATION
# ============================================================

BOT_NAME = "Veyra"
BOT_STUDIO = "Volbasty Studios"

DATA_DIR = Path(os.getenv("VEYRA_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = DATA_DIR / "logging_config.json"

# Replace these placeholders with your real animated Discord emojis.
# Format: <a:emoji_name:emoji_id>
EMOJI_LOADING = "<a:loading:EMOJI_ID>"
EMOJI_SUCCESS = "<a:success:EMOJI_ID>"
EMOJI_ERROR = "<a:error:EMOJI_ID>"
EMOJI_SECURITY = "<a:security:EMOJI_ID>"
EMOJI_LOGS = "<a:logs:EMOJI_ID>"
EMOJI_CANCEL = "<a:cancel:EMOJI_ID>"

# Unicode fallbacks work until real animated emojis are configured.
FALLBACK_LOADING = "🔄"
FALLBACK_SUCCESS = "✅"
FALLBACK_ERROR = "❌"
FALLBACK_SECURITY = "🛡️"
FALLBACK_LOGS = "📡"
FALLBACK_CANCEL = "✖️"

DEV_CHANNELS = [
    ("veyra-system-logs", "Bot startup, shutdown and system status."),
    ("veyra-command-logs", "Command names, user IDs and execution status."),
    ("veyra-ai-diagnostics", "AI model metadata, timings and request errors."),
    ("veyra-memory-logs", "Memory operation metadata, without message contents."),
    ("veyra-security-logs", "Permission denials and security-related events."),
    ("veyra-server-audit", "Veyra's server configuration and logging setup events."),
]

STANDARD_CHANNELS = [
    ("veyra-server-logs", "Veyra setup and server configuration events."),
    ("veyra-command-logs", "Command names, user IDs and execution status."),
    ("veyra-error-logs", "Bot errors and diagnostic information."),
]


def _emoji(placeholder: str, fallback: str) -> str:
    """Use the fallback until a real custom emoji ID is configured."""
    if "EMOJI_ID" in placeholder:
        return fallback
    return placeholder


def _load_config() -> dict:
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_config(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = CONFIG_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temporary_file.replace(CONFIG_FILE)


def _is_development_server(guild: discord.Guild) -> bool:
    return (
        DEVELOPMENT_GUILD_ID != 0
        and guild.id == DEVELOPMENT_GUILD_ID
    )


def _make_embed(
    title: str,
    description: str,
    color: discord.Color = discord.Color.from_rgb(48, 126, 190),
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    embed.set_footer(text=f"{BOT_NAME} • {BOT_STUDIO}")
    return embed


def _channel_plan(guild: discord.Guild) -> list[tuple[str, str]]:
    if _is_development_server(guild):
        return DEV_CHANNELS
    return STANDARD_CHANNELS


def _existing_log_category(guild: discord.Guild):
    for category in guild.categories:
        if category.name == "VEYRA LOGS":
            return category
    return None


def _permission_overwrites(
    guild: discord.Guild,
) -> dict:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        )
    }

    bot_member = guild.me
    if bot_member is not None:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
        )

    # The server owner always retains access. Administrators can
    # access private channels through Discord's administrator permission.
    owner = guild.owner
    if owner is not None:
        overwrites[owner] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )

    return overwrites


class LoggingSetupView(discord.ui.View):
    def __init__(
        self,
        requester_id: int,
        guild_id: int,
    ):
        super().__init__(timeout=120)
        self.requester_id = requester_id
        self.guild_id = guild_id
        self.finished = False

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "🔒 Only the administrator who started this setup "
                "can use these buttons.",
                ephemeral=True,
            )
            return False

        if interaction.guild_id != self.guild_id:
            await interaction.response.send_message(
                "❌ This setup belongs to a different server.",
                ephemeral=True,
            )
            return False

        member = interaction.user
        if not isinstance(member, discord.Member) or not is_server_admin(
            member, interaction.guild
        ):
            await interaction.response.send_message(
                "🛡️ You no longer have permission to configure logs.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Create Logs",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="veyra_logs_confirm",
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.finished:
            await interaction.response.send_message(
                "This setup has already finished.",
                ephemeral=True,
            )
            return

        self.finished = True
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=(
                f"{_emoji(EMOJI_LOADING, FALLBACK_LOADING)} "
                "**VEYRA // INITIALIZING LOGS**\n"
                "Creating the requested logging channels..."
            ),
            embed=None,
            view=self,
        )

        try:
            guild = interaction.guild
            if guild is None:
                raise RuntimeError("This command requires a server.")

            me = guild.me
            if me is None or not me.guild_permissions.manage_channels:
                raise PermissionError(
                    "Veyra needs the **Manage Channels** permission "
                    "to create logging channels."
                )

            config = _load_config()
            guild_key = str(guild.id)
            previous = config.get(guild_key, {})
            channel_ids = previous.get("channels", {})
            created_names = []
            failed_names = []

            category = _existing_log_category(guild)

            if category is None:
                category = await guild.create_category(
                    "VEYRA LOGS",
                    overwrites=_permission_overwrites(guild),
                    reason="Veyra logging setup confirmed by server admin",
                )

            # Reuse configured channels when they still exist.
            for channel_name, description in _channel_plan(guild):
                channel = guild.get_channel(channel_ids.get(channel_name, 0))

                if not isinstance(channel, discord.TextChannel):
                    channel = discord.utils.get(
                        category.text_channels,
                        name=channel_name,
                    )

                if channel is None:
                    try:
                        channel = await guild.create_text_channel(
                            channel_name,
                            category=category,
                            topic=(
                                f"{description} "
                                "Veyra diagnostic channel. "
                                "Do not post secrets or private data."
                            )[:1024],
                            overwrites=_permission_overwrites(guild),
                            reason="Veyra logging setup confirmed by server admin",
                        )
                        created_names.append(channel_name)
                        await asyncio.sleep(0.3)
                    except discord.HTTPException:
                        failed_names.append(channel_name)
                        continue
                else:
                    # Ensure an existing channel remains in the log category.
                    if channel.category_id != category.id:
                        try:
                            await channel.edit(
                                category=category,
                                overwrites=_permission_overwrites(guild),
                                reason="Organizing Veyra logging channels",
                            )
                        except discord.HTTPException:
                            failed_names.append(channel_name)
                            continue

                channel_ids[channel_name] = channel.id

            config[guild_key] = {
                "enabled": True,
                "category_id": category.id,
                "channels": channel_ids,
                "development_server": _is_development_server(guild),
                "configured_by": interaction.user.id,
            }
            _save_config(config)

            if failed_names:
                description = (
                    f"{_emoji(EMOJI_ERROR, FALLBACK_ERROR)} "
                    "**Setup completed with some errors.**\n\n"
                    f"Created: **{len(created_names)}** channel(s).\n"
                    f"Could not create or organize: "
                    f"`{', '.join(failed_names)}`\n\n"
                    "Check Veyra's permissions and server channel limits, "
                    "then run the setup again."
                )
                color = discord.Color.orange()
            else:
                description = (
                    f"{_emoji(EMOJI_SUCCESS, FALLBACK_SUCCESS)} "
                    "**LOGGING SYSTEM INITIALIZED**\n\n"
                    f"Logging category: **{category.name}**\n"
                    f"Channels created: **{len(created_names)}**\n"
                    f"Profile: **{'Development' if _is_development_server(guild) else 'Standard'}**\n\n"
                    "Your channel configuration has been saved."
                )
                color = discord.Color.green()

            embed = _make_embed(
                f"{_emoji(EMOJI_LOGS, FALLBACK_LOGS)}  VEYRA // LOGS READY",
                description,
                color,
            )

            channel_lines = []
            for channel_name, _ in _channel_plan(guild):
                channel_id = channel_ids.get(channel_name)
                if channel_id:
                    channel_lines.append(f"• <#{channel_id}>")

            if channel_lines:
                embed.add_field(
                    name="CONFIGURED CHANNELS",
                    value="\n".join(channel_lines),
                    inline=False,
                )

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=self,
            )

        except PermissionError as error:
            embed = _make_embed(
                "🛡️ PERMISSION REQUIRED",
                str(error),
                discord.Color.red(),
            )
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=self,
            )

        except (discord.HTTPException, OSError, RuntimeError) as error:
            # Do not expose internal exception details to the server.
            print(
                f"[VEYRA LOG SETUP ERROR] "
                f"guild_id={self.guild_id} "
                f"error_type={type(error).__name__}"
            )
            embed = _make_embed(
                "❌ LOG SETUP FAILED",
                "Veyra couldn't finish setting up the log channels. "
                "Check the bot's Manage Channels permission and hosting logs, "
                "then try again.",
                discord.Color.red(),
            )
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=self,
            )

    @discord.ui.button(
        label="Cancel",
        emoji="✖️",
        style=discord.ButtonStyle.secondary,
        custom_id="veyra_logs_cancel",
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.finished:
            await interaction.response.send_message(
                "This setup has already finished.",
                ephemeral=True,
            )
            return

        self.finished = True
        for child in self.children:
            child.disabled = True

        embed = _make_embed(
            "VEYRA // SETUP CANCELLED",
            f"{_emoji(EMOJI_CANCEL, FALLBACK_CANCEL)} "
            "No logging channels were created by this setup.",
            discord.Color.light_grey(),
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=self,
        )

    async def on_timeout(self):
        self.finished = True
        for child in self.children:
            child.disabled = True


async def handle_logs(message: discord.Message):
    """Handle !veyra logs."""
    if message.guild is None:
        await message.channel.send(
            "🛡️ The logging setup can only be used inside a server."
        )
        return

    if not isinstance(message.author, discord.Member):
        await message.channel.send("❌ I couldn't verify your server permissions.")
        return

    if not is_server_admin(message.author, message.guild):
        await message.channel.send(
            f"{_emoji(EMOJI_SECURITY, FALLBACK_SECURITY)} "
            "Only the server owner or an administrator with **Manage Server** "
            "permission can configure logging."
        )
        return

    if not message.guild.me or not message.guild.me.guild_permissions.manage_channels:
        await message.channel.send(
            "⚠️ I need the **Manage Channels** permission before I can create "
            "logging channels."
        )
        return

    plan = _channel_plan(message.guild)
    profile = "DEVELOPMENT" if _is_development_server(message.guild) else "STANDARD"

    embed = _make_embed(
        f"{_emoji(EMOJI_LOGS, FALLBACK_LOGS)}  VEYRA // SERVER LOGS",
        (
            f"Welcome to **{BOT_NAME}'s logging configuration**.\n\n"
            "Review the setup before continuing. Veyra will create a "
            "dedicated `VEYRA LOGS` category and the channels listed below.\n\n"
            f"**PROFILE:** `{profile}`\n"
            f"**CHANNELS:** `{len(plan)}`\n\n"
            "Nothing will be created until you press **Create Logs**."
        ),
    )

    embed.add_field(
        name="📡 CHANNEL PLAN",
        value="\n".join(
            f"**#{name}**\n{text}"
            for name, text in plan
        ),
        inline=False,
    )

    embed.add_field(
        name="🔒 PRIVACY & ACCESS",
        value=(
            "Channels are private to `@everyone` by default. "
            "The server owner and members with Administrator permission "
            "can access them. Veyra's logs should contain diagnostic metadata "
            "and redacted errors—not API keys or copied private conversations."
        ),
        inline=False,
    )

    embed.add_field(
        name="⚙️ REQUIREMENTS",
        value=(
            "• Veyra needs **Manage Channels**.\n"
            "• Channel creation is subject to server limits.\n"
            "• Existing Veyra logging channels may be reused."
        ),
        inline=False,
    )

    view = LoggingSetupView(
        requester_id=message.author.id,
        guild_id=message.guild.id,
    )

    await message.channel.send(embed=embed, view=view)
