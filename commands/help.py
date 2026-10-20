
import discord

from config import PREFIX


HELP_TEXT = {
    "en": {
        "title": "❄️ Veyra AI — Command Center",
        "description": "Prefix: `{prefix}`\nYour compact guide to Veyra.",
        "language": "🌐 Display language",
        "placeholder": "Choose help language...",
        "english": "English",
        "hindi": "हिन्दी (Hindi)",
        "language_desc_en": "Show the help menu in English",
        "language_desc_hi": "हेल्प मेनू हिंदी में दिखाएँ",
        "ai": "🤖 AI & Chat",
        "chat": "Quick chat mode",
        "longchat": "Detailed response mode",
        "memory": "View your memory info",
        "forget": "Clear your personal memory",
        "tools": "🛠️ Tools",
        "ping": "Check bot status",
        "codepro": "Coding assistance",
        "products": "Browse available tools",
        "product_usage": "Use a product with a question",
        "shop": "Open the shop",
        "admin": "🛡️ Server Admin",
        "setchannel": "Set the AI channel",
        "removechannel": "Remove the AI channel",
        "logs": "Configure bot logging",
        "developer": "👑 Developer",
        "devhelp": "View developer commands",
        "dev_note": "Developer commands require authorized access.",
        "footer": "VEYRA AI • Volbasty Studios",
        "denied": "Only the person who opened this help menu can change its language.",
        "expired": "This help menu has expired. Run the help command again.",
    },
    "hi": {
        "title": "❄️ Veyra AI — कमांड सेंटर",
        "description": "Prefix: `{prefix}`\nVeyra की छोटी-सी गाइड।",
        "language": "🌐 डिस्प्ले भाषा",
        "placeholder": "हेल्प की भाषा चुनें...",
        "english": "English",
        "hindi": "हिन्दी (Hindi)",
        "language_desc_en": "हेल्प मेनू अंग्रेज़ी में दिखाएँ",
        "language_desc_hi": "हेल्प मेनू हिंदी में दिखाएँ",
        "ai": "🤖 AI और चैट",
        "chat": "छोटे जवाब वाला चैट मोड",
        "longchat": "विस्तृत जवाब वाला मोड",
        "memory": "अपनी मेमोरी की जानकारी देखें",
        "forget": "अपनी पर्सनल मेमोरी मिटाएँ",
        "tools": "🛠️ टूल्स",
        "ping": "बॉट का स्टेटस जाँचें",
        "codepro": "कोडिंग में सहायता",
        "products": "उपलब्ध टूल्स देखें",
        "product_usage": "सवाल के साथ किसी प्रोडक्ट का उपयोग करें",
        "shop": "शॉप खोलें",
        "admin": "🛡️ सर्वर एडमिन",
        "setchannel": "AI चैनल सेट करें",
        "removechannel": "AI चैनल हटाएँ",
        "logs": "बॉट लॉगिंग सेट करें",
        "developer": "👑 डेवलपर",
        "devhelp": "डेवलपर कमांड देखें",
        "dev_note": "डेवलपर कमांड के लिए अधिकृत एक्सेस ज़रूरी है।",
        "footer": "VEYRA AI • Volbasty Studios",
        "denied": "इस हेल्प मेनू की भाषा केवल इसे खोलने वाला यूज़र बदल सकता है।",
        "expired": "यह हेल्प मेनू समाप्त हो गया है। दोबारा help कमांड चलाएँ।",
    },
}


def build_help_embed(prefix, language):
    text = HELP_TEXT[language]

    embed = discord.Embed(
        title=text["title"],
        description=text["description"].format(prefix=prefix),
        color=discord.Color.from_rgb(42, 164, 255),
    )

    embed.add_field(
        name=text["ai"],
        value=(
            f"`{prefix} chat` — {text['chat']}\n"
            f"`{prefix} longchat` — {text['longchat']}\n"
            f"`{prefix} memory` — {text['memory']}\n"
            f"`{prefix} forget` — {text['forget']}"
        ),
        inline=False,
    )

    embed.add_field(
        name=text["tools"],
        value=(
            f"`{prefix} ping` — {text['ping']}\n"
            f"`{prefix} codepro <task>` — {text['codepro']}\n"
            f"`{prefix} products` — {text['products']}\n"
            f"`{prefix} <product> <question>` — {text['product_usage']}\n"
            f"`{prefix} shop` — {text['shop']}"
        ),
        inline=False,
    )

    embed.add_field(
        name=text["admin"],
        value=(
            f"`{prefix} setchannel #channel` — {text['setchannel']}\n"
            f"`{prefix} removechannel #channel` — {text['removechannel']}\n"
            f"`{prefix} logs` — {text['logs']}"
        ),
        inline=False,
    )

    embed.add_field(
        name=text["developer"],
        value=(
            f"`{prefix} devhelp` — {text['devhelp']}\n"
            f"{text['dev_note']}"
        ),
        inline=False,
    )

    embed.set_footer(text=text["footer"])
    return embed


class HelpLanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="English",
                value="en",
                emoji="🇬🇧",
                description="Show the help menu in English",
                default=True,
            ),
            discord.SelectOption(
                label="हिन्दी (Hindi)",
                value="hi",
                emoji="🇮🇳",
                description="हेल्प मेनू हिंदी में दिखाएँ",
            ),
        ]

        super().__init__(
            placeholder="🌐 Choose help language / भाषा चुनें",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="veyra_help_language",
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if not isinstance(view, HelpLanguageView):
            return

        if interaction.user.id != view.owner_id:
            await interaction.response.send_message(
                HELP_TEXT[view.language]["denied"],
                ephemeral=True,
            )
            return

        language = self.values[0]
        view.language = language

        # Update the selected option in the dropdown.
        for option in self.options:
            option.default = option.value == language

        await interaction.response.edit_message(
            embed=build_help_embed(view.prefix, language),
            view=view,
        )


class HelpLanguageView(discord.ui.View):
    def __init__(self, owner_id, prefix):
        super().__init__(timeout=300)

        self.owner_id = owner_id
        self.prefix = prefix
        self.language = "en"

        self.add_item(HelpLanguageSelect())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the person who opened this help menu can use its dropdown.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        # The original message may no longer be editable.
        if getattr(self, "message", None):
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass


async def handle_help(message, prefix=PREFIX):
    view = HelpLanguageView(
        owner_id=message.author.id,
        prefix=prefix,
    )

    sent_message = await message.reply(
        embed=build_help_embed(prefix, "en"),
        view=view,
        mention_author=False,
        allowed_mentions=discord.AllowedMentions.none(),
    )

    view.message = sent_message
