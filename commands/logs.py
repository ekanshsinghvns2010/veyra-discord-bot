
import os
import json
import asyncio
import discord
from pathlib import Path

from config import PREFIX, DEVELOPMENT_GUILD_ID
from security.permissions import is_server_admin


BOT_NAME = "Veyra"
BOT_STUDIO = "Volbasty Studios"

DATA_DIR = Path(os.getenv("VEYRA_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "logging_config.json"

EMOJI_LOADING = "<a:loading:1562036543236083823>"
EMOJI_SUCCESS = "<a:success:1562036339019489390>"
EMOJI_ERROR = "<a:error:1562036219674890240>"
EMOJI_SECURITY = "<:security:1562036145515266169>"
EMOJI_LOGS = "<:logs:1562036061620797473>"
EMOJI_CANCEL = "<a:cancel:1562035965722234991>"

FALLBACK_LOADING = "🔄"
FALLBACK_SUCCESS = "✅"
FALLBACK_ERROR = "❌"
FALLBACK_SECURITY = "🛡️"
FALLBACK_LOGS = "📡"
FALLBACK_CANCEL = "✖️"

DEV_CHANNELS = [
    ("veyra-system-logs", "Bot startup and system status."),
    ("veyra-command-logs", "Command names, user IDs and status."),
    ("veyra-ai-diagnostics", "AI request status and mode metadata."),
    ("veyra-memory-logs", "Memory operation metadata."),
    ("veyra-security-logs", "Permission denials and security events."),
    ("veyra-server-audit", "Server configuration events."),
]

STANDARD_CHANNELS = [
    ("veyra-server-logs", "Veyra setup and general diagnostic events."),
    ("veyra-command-logs", "Command names, user IDs and status."),
    ("veyra-error-logs", "Bot errors and diagnostic information."),
]


def _emoji(placeholder, fallback):
    return fallback if "EMOJI_ID" in placeholder else placeholder


def _load_config():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_config(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = CONFIG_FILE.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
    temporary_file.replace(CONFIG_FILE)


def _is_development_server(guild):
    return DEVELOPMENT_GUILD_ID != 0 and guild.id == DEVELOPMENT_GUILD_ID


def _make_embed(title, description, color=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.from_rgb(48, 126, 190),
    )
    embed.set_footer(text=f"{BOT_NAME} • {BOT_STUDIO}")
    return embed


def _channel_plan(guild):
    return DEV_CHANNELS if _is_development_server(guild) else STANDARD_CHANNELS


def _existing_log_category(guild):
    return discord.utils.get(guild.categories, name="VEYRA LOGS")


def _permission_overwrites(guild):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }

    me = guild.me
    if me is not None:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
        )

    owner = guild.owner
    if owner is not None:
        overwrites[owner] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )

    return overwrites


class LoggingSetupView(discord.ui.View):
    def __init__(self, requester_id, guild_id):
        super().__init__(timeout=120)
        self.requester_id = requester_id
        self.guild_id = guild_id
        self.finished = False

    async def interaction_check(self, interaction):
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "🔒 Only the administrator who started setup can use these buttons.",
                ephemeral=True,
            )
            return False

        if interaction.guild_id != self.guild_id:
            await interaction.response.send_message(
                "❌ This setup belongs to another server.",
                ephemeral=True,
            )
            return False

        if (
            interaction.guild is None
            or not isinstance(interaction.user, discord.Member)
            or not is_server_admin(interaction.user, interaction.guild)
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
    async def confirm(self, interaction, button):
        if self.finished:
            await interaction.response.send_message(
                "This setup has already finished.", ephemeral=True
            )
            return

        self.finished = True
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"{_emoji(EMOJI_LOADING, FALLBACK_LOADING)} **VEYRA // INITIALIZING LOGS**",
            embed=None,
            view=self,
        )

        try:
            guild = interaction.guild
            if guild is None:
                raise RuntimeError("This command requires a server.")

            me = guild.me
            if me is None or not me.guild_permissions.manage_channels:
                raise PermissionError("Veyra needs the Manage Channels permission.")

            config = _load_config()
            guild_key = str(guild.id)
            previous = config.get(guild_key, {})
            if not isinstance(previous, dict):
                previous = {}

            channel_ids = previous.get("channels", {})
            if not isinstance(channel_ids, dict):
                channel_ids = {}

            category = _existing_log_category(guild)
            if category is None:
                category = await guild.create_category(
                    "VEYRA LOGS",
                    overwrites=_permission_overwrites(guild),
                    reason="Veyra logging setup confirmed by server admin",
                )

            created_names = []
            failed_names = []

            for channel_name, description in _channel_plan(guild):
                channel = None
                saved_id = channel_ids.get(channel_name)

                if saved_id:
                    try:
                        channel = guild.get_channel(int(saved_id))
                    except (TypeError, ValueError):
                        channel = None

                if not isinstance(channel, discord.TextChannel):
                    channel = discord.utils.get(
                        category.text_channels, name=channel_name
                    )

                if channel is None:
                    try:
                        channel = await guild.create_text_channel(
                            channel_name,
                            category=category,
                            topic=(description + " Do not post secrets or private data.")[:1024],
                            overwrites=_permission_overwrites(guild),
                            reason="Veyra logging setup confirmed by server admin",
                        )
                        created_names.append(channel_name)
                        await asyncio.sleep(0.2)
                    except discord.HTTPException:
                        failed_names.append(channel_name)
                        continue
                else:
                    try:
                        await channel.edit(
                            category=category,
                            overwrites=_permission_overwrites(guild),
                            reason="Updating Veyra logging channel permissions",
                        )
                    except discord.HTTPException:
                        failed_names.append(channel_name)
                        continue

                channel_ids[channel_name] = channel.id

            config[guild_key] = {
                **previous,
                "enabled": True,
                "category_id": category.id,
                "channels": channel_ids,
                "development_server": _is_development_server(guild),
                "configured_by": interaction.user.id,
            }
            _save_config(config)

            failed_text = (
                "\nCould not configure: " + ", ".join(failed_names)
                if failed_names else ""
            )
            status = (
                "LOGGING ENABLED" if not failed_names
                else "LOGGING ENABLED WITH WARNINGS"
            )
            color = discord.Color.green() if not failed_names else discord.Color.orange()

            embed = _make_embed(
                f"{_emoji(EMOJI_LOGS, FALLBACK_LOGS)} VEYRA // {status}",
                (
                    f"{_emoji(EMOJI_SUCCESS, FALLBACK_SUCCESS)} "
                    f"Profile: **{'Development' if _is_development_server(guild) else 'Standard'}**\n"
                    f"Category: **{category.name}**\n"
                    f"New channels created: **{len(created_names)}**"
                    f"{failed_text}\n\n"
                    "The configuration has been saved. Event logging will work "
                    "when the logging service is installed and the bot is restarted."
                ),
                color,
            )

            lines = [
                f"• <#{channel_ids[name]}>"
                for name, _ in _channel_plan(guild)
                if name in channel_ids
            ]
            if lines:
                embed.add_field(
                    name="CONFIGURED CHANNELS",
                    value="\n".join(lines),
                    inline=False,
                )

            await interaction.edit_original_response(
                content=None, embed=embed, view=self
            )

        except PermissionError as error:
            await interaction.edit_original_response(
                content=None,
                embed=_make_embed("🛡️ PERMISSION REQUIRED", str(error), discord.Color.red()),
                view=self,
            )
        except (discord.HTTPException, OSError, RuntimeError, ValueError) as error:
            print(
                f"[VEYRA LOG SETUP ERROR] guild_id={self.guild_id} "
                f"type={type(error).__name__}"
            )
            await interaction.edit_original_response(
                content=None,
                embed=_make_embed(
                    "❌ LOG SETUP FAILED",
                    "Veyra couldn't finish setting up logging. Check Manage Channels "
                    "permission and the hosting console, then try again.",
                    discord.Color.red(),
                ),
                view=self,
            )

    @discord.ui.button(
        label="Cancel",
        emoji="✖️",
        style=discord.ButtonStyle.secondary,
        custom_id="veyra_logs_cancel",
    )
    async def cancel(self, interaction, button):
        if self.finished:
            await interaction.response.send_message(
                "This setup has already finished.", ephemeral=True
            )
            return

        self.finished = True
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=None,
            embed=_make_embed(
                "VEYRA // SETUP CANCELLED",
                f"{_emoji(EMOJI_CANCEL, FALLBACK_CANCEL)} No channels were created by this setup.",
                discord.Color.light_grey(),
            ),
            view=self,
        )

    async def on_timeout(self):
        self.finished = True
        for child in self.children:
            child.disabled = True


async def handle_logs(message):
    if message.guild is None:
        await message.channel.send("🛡️ Logging setup can only be used inside a server.")
        return

    if (
        not isinstance(message.author, discord.Member)
        or not is_server_admin(message.author, message.guild)
    ):
        await message.channel.send(
            f"{_emoji(EMOJI_SECURITY, FALLBACK_SECURITY)} Only the server owner "
            "or a server administrator can configure logging."
        )
        return

    me = message.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await message.channel.send(
            "⚠️ I need the **Manage Channels** permission to create logging channels."
        )
        return

    plan = _channel_plan(message.guild)
    profile = "DEVELOPMENT" if _is_development_server(message.guild) else "STANDARD"

    embed = _make_embed(
        f"{_emoji(EMOJI_LOGS, FALLBACK_LOGS)} VEYRA // SERVER LOGS",
        (
            "Review the logging setup below. Nothing will be created until "
            "you press **Create Logs**.\n\n"
            f"**Profile:** `{profile}`\n**Channels:** `{len(plan)}`"
        ),
    )
    embed.add_field(
        name="📡 CHANNEL PLAN",
        value="\n".join(f"**#{name}**\n{description}" for name, description in plan),
        inline=False,
    )
    embed.add_field(
        name="🔒 PRIVACY & ACCESS",
        value=(
            "Channels are hidden from @everyone by default. Administrators "
            "can access them. Logs contain event metadata, not copied AI chats "
            "or API secrets."
        ),
        inline=False,
    )
    embed.add_field(
        name="⚙️ REQUIREMENTS",
        value="• Veyra needs **Manage Channels**.\n• Server channel limits apply.",
        inline=False,
    )

    await message.channel.send(
        embed=embed,
        view=LoggingSetupView(message.author.id, message.guild.id),
    )
