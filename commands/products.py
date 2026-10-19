
import asyncio
import json
import os
from pathlib import Path

import discord

from ai_client import ask_veyra

ICE_BLUE = discord.Color.from_rgb(42, 164, 255)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ACCESS_FILE = DATA_DIR / "product_access.json"

PRODUCTS = {
    "code": {
        "name": "Veyra Code",
        "pro_name": "Code Pro",
        "emoji": "💻",
        "tagline": "Build beyond the basics.",
        "features": [
            "Code explanations and examples",
            "Basic debugging assistance",
            "Help understanding errors",
        ],
        "pro_features": [
            "Advanced debugging and code reviews",
            "Multi-file implementation planning",
            "Complex project assistance",
        ],
        "free_limit": 30,
    },
    "study": {
        "name": "Veyra Study",
        "pro_name": "Study Pro",
        "emoji": "📚",
        "tagline": "Turn difficult topics into clear knowledge.",
        "features": [
            "Concept explanations",
            "Short revision notes",
            "Basic practice questions",
        ],
        "pro_features": [
            "Detailed chapter notes",
            "Structured revision plans",
            "Extended quizzes and practice",
        ],
        "free_limit": 10,
    },
    "research": {
        "name": "Veyra Research",
        "pro_name": "Deep Research Pro",
        "emoji": "🔎",
        "tagline": "Explore beyond the first answer.",
        "features": [
            "Research planning",
            "General explanations",
            "Limited web-search integration when available",
        ],
        "pro_features": [
            "Multi-step web research",
            "Source-linked reports",
            "Cross-source comparisons",
        ],
        "free_limit": 3,
    },
}


def load_access():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not ACCESS_FILE.exists():
        return {}

    try:
        with ACCESS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        print("[PRODUCTS] Could not read product_access.json")
        return {}


def save_access(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = ACCESS_FILE.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    temporary.replace(ACCESS_FILE)


def get_tier(user_id, product_id):
    data = load_access()
    user = data.get(str(user_id), {})
    tier = user.get(product_id, "free")

    # Never accept arbitrary values as Pro.
    return "pro" if tier == "pro" else "free"


def set_tier(user_id, product_id, tier):
    if tier not in {"free", "pro"}:
        raise ValueError("Tier must be free or pro.")

    data = load_access()
    user = data.setdefault(str(user_id), {})
    user[product_id] = tier
    save_access(data)


def product_embed(product_id, user_id, server_name):
    product = PRODUCTS[product_id]
    tier = get_tier(user_id, product_id)
    is_pro = tier == "pro"

    embed = discord.Embed(
        title=f"{product['emoji']} {product['name']} Workspace",
        description=(
            f"*{product['tagline']}*\n\n"
            f"**Account tier:** {'⚡ PRO' if is_pro else '🆓 FREE'}\n"
            f"**Server:** {server_name}\n\n"
            "Choose an action below to continue."
        ),
        color=ICE_BLUE,
    )

    features = product["pro_features"] if is_pro else product["features"]

    embed.add_field(
        name="✨ Available features",
        value="\n".join(f"• {item}" for item in features),
        inline=False,
    )

    if not is_pro:
        embed.add_field(
            name="⚡ Upgrade",
            value=(
                f"Unlock {product['pro_name']} for expanded capabilities. "
                "Use `!veyra shop` to view the current product listing."
            ),
            inline=False,
        )

    embed.set_footer(
        text="VEYRA AI • BY VOLBASTY STUDIOS"
    )
    return embed


class ProductView(discord.ui.View):
    def __init__(self, product_id, user_id, server_name):
        super().__init__(timeout=180)
        self.product_id = product_id
        self.user_id = user_id
        self.server_name = server_name

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This workspace belongs to another user. "
                "Run your own activation command.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Refresh Access",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def refresh(self, interaction, button):
        await interaction.response.edit_message(
            embed=product_embed(
                self.product_id,
                self.user_id,
                self.server_name,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Product Help",
        emoji="❔",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def help_button(self, interaction, button):
        product = PRODUCTS[self.product_id]
        tier = get_tier(self.user_id, self.product_id)

        await interaction.response.send_message(
            f"**{product['name']} Help**\n"
            f"Current tier: **{tier.upper()}**\n"
            f"Use `!veyra {self.product_id}` to reopen this workspace.\n"
            "Use `!veyra products` to view all products.",
            ephemeral=True,
        )


async def activate_product(message, product_id):
    if message.guild is None:
        await message.reply("Activate products inside a Discord server.")
        return

    product = PRODUCTS[product_id]

    # Check access before displaying the final workspace.
    tier = get_tier(message.author.id, product_id)

    loading = discord.Embed(
        title="❄️ VEYRA INTELLIGENCE",
        description=(
            "```ansi\n"
            "\u001b[1;36mINITIALIZING PRODUCT ENVIRONMENT\u001b[0m\n"
            "```\n"
            "◈ Verifying product access...\n"
            "◈ Preparing your workspace...\n"
            "◈ Loading AI configuration...\n\n"
            "*Please wait while Veyra gets things ready.*"
        ),
        color=ICE_BLUE,
    )
    loading.set_footer(text="VOLBASTY STUDIOS • INITIALIZATION")

    message_to_edit = await message.reply(
        embed=loading,
        mention_author=False,
    )

    # Intentional UI delay, not a claim of actual background processing.
    await asyncio.sleep(4.5)

    view = ProductView(
        product_id,
        message.author.id,
        message.guild.name,
    )

    await message_to_edit.edit(
        embed=product_embed(
            product_id,
            message.author.id,
            message.guild.name,
        ),
        view=view,
    )


async def handle_products(message):
    embed = discord.Embed(
        title="❄️ VEYRA PRODUCTS",
        description="Choose a product to activate its Free or Pro workspace.",
        color=ICE_BLUE,
    )

    for key, product in PRODUCTS.items():
        tier = get_tier(message.author.id, key)
        embed.add_field(
            name=f"{product['emoji']} {product['name']}",
            value=f"Account tier: **{tier.upper()}**\n"
                  f"Activate with `!veyra {key}`",
            inline=False,
        )

    embed.set_footer(text="VEYRA AI • BY VOLBASTY STUDIOS")
    await message.reply(embed=embed, mention_author=False)


async def handle_product_command(message, product_id):
    if product_id not in PRODUCTS:
        return

    await activate_product(message, product_id)


# Owner-only manual entitlement grant.
# Configure VEYRA_OWNER_ID in your hosting environment.
async def handle_grant_pro(message, args):
    owner_id = os.getenv("VEYRA_OWNER_ID", "").strip()

    if not owner_id or str(message.author.id) != owner_id:
        await message.reply("🔒 Only the bot owner can grant Pro access.")
        return

    if len(args) != 3:
        await message.reply(
            "Usage: `!veyra grantpro @user code|study|research`"
        )
        return

    target = message.mentions[0] if message.mentions else None
    product_id = args[2].lower()

    if target is None or product_id not in PRODUCTS:
        await message.reply(
            "Mention a valid user and choose `code`, `study`, or `research`."
        )
        return

    set_tier(target.id, product_id, "pro")

    await message.reply(
        f"✅ Granted **{PRODUCTS[product_id]['pro_name']}** to "
        f"{target.mention}.\n"
        "This records a manual owner grant; it does not process a payment."
    )


async def handle_ask_product(message, product_id, prompt):
    if product_id not in PRODUCTS:
        return

    if not prompt.strip():
        await message.reply(
            f"Add your question after the command, for example:\n"
            f"`!veyra {product_id} Explain this topic`"
        )
        return

    tier = get_tier(message.author.id, product_id)
    product = PRODUCTS[product_id]

    system_prompt = {
        "code": (
            "You are Veyra Code, a coding assistant. Explain errors, "
            "write understandable code, and prefer practical solutions. "
            + (
                "For this Pro account, provide deeper reviews and "
                "multi-file implementation plans when useful."
                if tier == "pro" else
                "For Free, focus on concise explanations and small examples."
            )
        ),
        "study": (
            "You are Veyra Study, a patient tutor. Teach concepts clearly, "
            "use examples, and create practice questions when requested. "
            + (
                "For Pro, provide detailed notes and structured revision."
                if tier == "pro" else
                "For Free, keep notes and explanations concise."
            )
        ),
        "research": (
            "You are Veyra Research. Be careful with factual claims, "
            "separate known facts from uncertainty, and never invent "
            "sources or claim you searched the web unless a search tool "
            "actually ran. "
            + (
                "For Pro, prepare structured research reports when "
                "appropriate, but use live search only if configured."
                if tier == "pro" else
                "For Free, give a concise answer and state when live "
                "verification is needed."
            )
        ),
    }[product_id]

    status = discord.Embed(
        title=f"{product['emoji']} {product['name']} is working...",
        description="Preparing your response. Please wait.",
        color=ICE_BLUE,
    )
    reply_message = await message.reply(
        embed=status,
        mention_author=False,
    )

    try:
        answer = await ask_veyra(
    prompt=f"{system_prompt}\n\nUser request:\n{prompt}",
    mode="deep" if tier == "pro" else "chat",
    web_search=(product_id == "research" and tier == "pro"),
)

        answer = str(answer or "I couldn't generate a response.")
        result = discord.Embed(
            title=f"{product['emoji']} {product['name']}",
            description=answer[:4000],
            color=ICE_BLUE,
        )
        result.set_footer(
            text=f"{tier.upper()} • VEYRA AI • VOLBASTY STUDIOS"
        )

        await reply_message.edit(embed=result)

    except Exception as error:
        print(f"[PRODUCT ERROR] {product_id}: {type(error).__name__}: {error}")
        await reply_message.edit(
            embed=discord.Embed(
                title="⚠️ Product temporarily unavailable",
                description=(
                    "Veyra couldn't complete that request. Please try again."
                ),
                color=discord.Color.orange(),
            )
        )
