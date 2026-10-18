
import discord

from config import PREFIX


BLUE = discord.Color.from_rgb(35, 160, 255)


def build_help_embed(language: str, prefix: str) -> discord.Embed:
    """Build Veyra's help embed in English or Hindi."""

    if language == "hi":
        embed = discord.Embed(
            title="❄️ VEYRA AI",
            description=(
                "**कमांड सेंटर**\n"
                "आपकी AI यात्रा में आपका स्वागत है!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "💠 **AI चैट**\n"
                "निर्धारित सर्वर चैनल में सामान्य तरीके से बात करें।"
            ),
            color=BLUE,
        )

        embed.add_field(
            name="⚡ सामान्य कमांड",
            value=(
                f"`{prefix} help` — सहायता मेनू खोलें\n"
                f"`{prefix} guide` — उपयोग गाइड देखें\n"
                f"`{prefix} ping` — बॉट की स्थिति जाँचें\n"
                f"`{prefix} memory` — अपनी सेव की गई मेमोरी देखें\n"
                f"`{prefix} forget` — अपनी मेमोरी मिटाएँ\n"
                f"`{prefix} shop` — Code Pro, Study Pro और Deep Research देखें"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛠️ सर्वर मैनेजमेंट",
            value=(
                f"`{prefix} setchannel #channel` — AI चैनल सेट करें\n"
                f"`{prefix} removechannel` — AI चैनल हटाएँ\n"
                f"`{prefix} chat` — छोटे जवाबों वाला मोड\n"
                f"`{prefix} longchat` — विस्तृत जवाबों वाला मोड"
            ),
            inline=False,
        )

        embed.add_field(
            name="🌌 VEYRA का उपयोग कैसे करें",
            value=(
                "**01** सवाल पूछने के लिए निर्धारित चैट चैनल का उपयोग करें।\n"
                "**02** अपनी पसंदीदा भाषा में बात करें।\n"
                "**03** `memory` से सेव की गई जानकारी देखें।\n"
                "**04** `forget` से अपनी मेमोरी साफ़ करें।\n"
                "**05** `shop` से उपलब्ध प्रीमियम विकल्प देखें।"
            ),
            inline=False,
        )

        embed.add_field(
            name="🔐 अनुमतियाँ",
            value=(
                "चैनल और चैट मोड बदलने के लिए सर्वर मालिक "
                "या एडमिन की अनुमति आवश्यक है।\n\n"
                "मेमोरी कमांड केवल आपकी अपनी मेमोरी पर असर डालते हैं।"
            ),
            inline=False,
        )

    else:
        embed = discord.Embed(
            title="❄️ VEYRA AI",
            description=(
                "**COMMAND CENTER**\n"
                "Your gateway to intelligence beyond limits.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "💠 **AI CHAT**\n"
                "Chat naturally in the configured server channel."
            ),
            color=BLUE,
        )

        embed.add_field(
            name="⚡ GENERAL COMMANDS",
            value=(
                f"`{prefix} help` — Display this command guide\n"
                f"`{prefix} guide` — Open the help guide\n"
                f"`{prefix} ping` — Check bot status\n"
                f"`{prefix} memory` — View your saved memory privately\n"
                f"`{prefix} forget` — Clear your saved memory\n"
                f"`{prefix} shop` — Explore Code Pro, Study Pro & Deep Research"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛠️ SERVER MANAGEMENT",
            value=(
                f"`{prefix} setchannel #channel` — Configure the AI channel\n"
                f"`{prefix} removechannel` — Remove the AI channel\n"
                f"`{prefix} chat` — Switch to quick-response mode\n"
                f"`{prefix} longchat` — Switch to detailed-response mode"
            ),
            inline=False,
        )

        embed.add_field(
            name="🌌 HOW TO USE VEYRA",
            value=(
                "**01** Ask questions in the configured chat channel.\n"
                "**02** Chat naturally in your preferred language.\n"
                "**03** Use `memory` to review saved context.\n"
                "**04** Use `forget` to clear your saved memory.\n"
                "**05** Use `shop` to explore premium options."
            ),
            inline=False,
        )

        embed.add_field(
            name="🔐 PERMISSIONS",
            value=(
                "Channel configuration and response-mode changes "
                "require server owner or administrator permissions.\n\n"
                "Memory commands affect only your own saved memory."
            ),
            inline=False,
        )

    embed.set_footer(
        text="VEYRA AI • Powered by Volbasty Studios"
    )

    return embed


class HelpLanguageSelect(discord.ui.Select):
    def __init__(self, owner_id: int, prefix: str):
        self.owner_id = owner_id
        self.prefix = prefix

        options = [
            discord.SelectOption(
                label="English",
                value="en",
                emoji="🇬🇧",
                description="View the help menu in English",
                default=True,
            ),
            discord.SelectOption(
                label="Hindi",
                value="hi",
                emoji="🇮🇳",
                description="हिंदी में सहायता मेनू देखें",
            ),
        ]

        super().__init__(
            placeholder="🌐 Choose language / भाषा चुनें",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the person who opened this help menu "
                "can change its language.",
                ephemeral=True,
            )
            return

        language = self.values[0]

        for option in self.options:
            option.default = option.value == language

        await interaction.response.edit_message(
            embed=build_help_embed(language, self.prefix),
            view=self.view,
        )


class HelpView(discord.ui.View):
    def __init__(self, owner_id: int, prefix: str):
        super().__init__(timeout=180)
        self.add_item(HelpLanguageSelect(owner_id, prefix))


async def handle_help(message, prefix=None):
    """Send Veyra's help menu with a language selector."""

    if prefix is None:
        prefix = PREFIX

    embed = build_help_embed("en", prefix)
    view = HelpView(message.author.id, prefix)

    await message.reply(
        embed=embed,
        view=view,
        mention_author=False,
    )
