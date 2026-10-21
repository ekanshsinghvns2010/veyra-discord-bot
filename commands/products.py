
import asyncio
import json
import os
import re
from pathlib import Path

import discord

from ai_client import ask_veyra

ICE_BLUE = discord.Color.from_rgb(42, 164, 255)
EMBED_CHUNK_SIZE = 3800

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

    except (OSError, json.JSONDecodeError) as error:
        print(
            f"[PRODUCTS] Could not read access file: "
            f"{type(error).__name__}: {error}",
            flush=True,
        )
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

    if not isinstance(user, dict):
        return "free"

    return "pro" if user.get(product_id) == "pro" else "free"


def set_tier(user_id, product_id, tier):
    if product_id not in PRODUCTS:
        raise ValueError("Unknown product.")

    if tier not in {"free", "pro"}:
        raise ValueError("Tier must be free or pro.")

    data = load_access()
    user = data.setdefault(str(user_id), {})

    if not isinstance(user, dict):
        user = {}
        data[str(user_id)] = user

    user[product_id] = tier
    save_access(data)


def count_pro_users():
    """Count unique users with Pro access to at least one product."""
    data = load_access()

    return sum(
        1
        for access in data.values()
        if isinstance(access, dict)
        and any(
            access.get(product_id) == "pro"
            for product_id in PRODUCTS
        )
    )


def split_answer(text, limit=EMBED_CHUNK_SIZE):
    """Split long AI answers into embed-safe chunks."""
    text = str(text or "").strip()

    if not text:
        return ["I couldn't generate a response. Please try again."]

    chunks = []

    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit + 1)

        if split_at < limit // 2:
            split_at = text.rfind(" ", 0, limit + 1)

        if split_at < limit // 2:
            split_at = limit

        chunk = text[:split_at].strip()

        if chunk:
            chunks.append(chunk)

        text = text[split_at:].strip()

    if text:
        chunks.append(text)

    return chunks or ["I couldn't generate a response. Please try again."]


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

    features = (
        product["pro_features"]
        if is_pro
        else product["features"]
    )

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

    embed.set_footer(text="VEYRA AI • BY VOLBASTY STUDIOS")
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
        await message.reply(
            "Activate products inside a Discord server.",
            mention_author=False,
        )
        return

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
            value=(
                f"Account tier: **{tier.upper()}**\n"
                f"Activate with `!veyra {key}`"
            ),
            inline=False,
        )

    embed.set_footer(text="VEYRA AI • BY VOLBASTY STUDIOS")

    await message.reply(
        embed=embed,
        mention_author=False,
    )


async def handle_product_command(message, product_id):
    if product_id not in PRODUCTS:
        return

    await activate_product(message, product_id)


async def handle_grant_pro(message, args):
    """Grant a product's Pro entitlement to a server member."""

    owner_id = os.getenv("VEYRA_OWNER_ID", "").strip()

    if not owner_id or str(message.author.id) != owner_id:
        await message.reply(
            "🔒 Only the configured bot owner can grant Pro access.",
            mention_author=False,
        )
        return

    target = message.mentions[0] if message.mentions else None

    if target is None and message.guild is not None:
        match = re.search(r"<@!?(\d+)>", message.content)

        if match:
            target_id = int(match.group(1))
            target = message.guild.get_member(target_id)

    tokens = re.split(r"\s+", message.content.strip())

    product_id = next(
        (
            token.lower()
            for token in tokens
            if token.lower() in PRODUCTS
        ),
        None,
    )

    if message.guild is None:
        await message.reply(
            "Run this command inside a Discord server.",
            mention_author=False,
        )
        return

    if target is None or product_id is None:
        await message.reply(
            "❌ I couldn't identify the member or product.\n"
            "Usage: `!veyra grantpro @user research`\n"
            "Available products: `code`, `study`, `research`",
            mention_author=False,
        )
        return

    try:
        set_tier(target.id, product_id, "pro")

    except (OSError, ValueError) as error:
        print(
            f"[GRANT PRO ERROR] {type(error).__name__}: {error}",
            flush=True,
        )

        await message.reply(
            "❌ I couldn't save the Pro entitlement. Check the bot logs.",
            mention_author=False,
        )
        return

    print(
        f"[GRANT PRO] Owner {message.author.id} granted "
        f"{product_id} Pro to user {target.id}.",
        flush=True,
    )

    await message.reply(
        f"✅ Granted **{PRODUCTS[product_id]['pro_name']}** to "
        f"{target.mention}.\n"
        f"Product: **{PRODUCTS[product_id]['name']}**\n"
        "This is a manual owner grant; no payment was processed.",
        mention_author=False,
    )


async def handle_remove_pro(message):
    """Revoke Pro access from a member or from every user."""

    owner_id = os.getenv("VEYRA_OWNER_ID", "").strip()

    if not owner_id or str(message.author.id) != owner_id:
        await message.reply(
            "🔒 Only the configured bot owner can remove Pro access.",
            mention_author=False,
        )
        return

    if message.guild is None:
        await message.reply(
            "Run this command inside a Discord server.",
            mention_author=False,
        )
        return

    tokens = message.content.split()
    args = tokens[2:] if len(tokens) > 2 else []

    # Global removal: !veyra removepro everyone
    if any(token.lower() == "everyone" for token in args):
        data = load_access()
        revoked = 0

        for access in data.values():
            if not isinstance(access, dict):
                continue

            for product_id in PRODUCTS:
                if access.get(product_id) == "pro":
                    access[product_id] = "free"
                    revoked += 1

        try:
            save_access(data)
        except OSError as error:
            print(
                f"[REMOVE PRO ERROR] {type(error).__name__}: {error}",
                flush=True,
            )
            await message.reply(
                "❌ I couldn't save the changes. Check the bot logs.",
                mention_author=False,
            )
            return

        print(
            f"[REMOVE PRO] Owner {message.author.id} revoked "
            f"{revoked} Pro entitlements globally.",
            flush=True,
        )

        await message.reply(
            "✅ **Global Pro access removal complete.**\n"
            f"**Pro entitlements revoked:** {revoked}\n"
            f"**Users still holding Pro:** {count_pro_users()}",
            mention_author=False,
        )
        return

    # Individual removal: !veyra removepro @user code
    # Or all products for one user: !veyra removepro @user all
    target = message.mentions[0] if message.mentions else None

    if target is None:
        match = re.search(r"<@!?(\d+)>", message.content)

        if match:
            target = message.guild.get_member(int(match.group(1)))

    product_id = next(
        (
            token.lower()
            for token in args
            if token.lower() in PRODUCTS
        ),
        None,
    )

    remove_all = any(
        token.lower() == "all"
        for token in args
    )

    if target is None or (product_id is None and not remove_all):
        await message.reply(
            "❌ I couldn't identify the member or product.\n\n"
            "Usage:\n"
            "`!veyra removepro @user code`\n"
            "`!veyra removepro @user all`\n"
            "`!veyra removepro everyone`\n\n"
            "Products: `code`, `study`, `research`",
            mention_author=False,
        )
        return

    data = load_access()
    user_id = str(target.id)
    access = data.get(user_id, {})

    if not isinstance(access, dict):
        access = {}
        data[user_id] = access

    product_ids = list(PRODUCTS) if remove_all else [product_id]

    revoked = [
        pid
        for pid in product_ids
        if access.get(pid) == "pro"
    ]

    for pid in revoked:
        access[pid] = "free"

    try:
        save_access(data)
    except OSError as error:
        print(
            f"[REMOVE PRO ERROR] {type(error).__name__}: {error}",
            flush=True,
        )
        await message.reply(
            "❌ I couldn't save the changes. Check the bot logs.",
            mention_author=False,
        )
        return

    if not revoked:
        await message.reply(
            f"ℹ️ {target.mention} has no matching Pro access to remove.",
            mention_author=False,
        )
        return

    names = ", ".join(
        PRODUCTS[pid]["pro_name"]
        for pid in revoked
    )

    print(
        f"[REMOVE PRO] Owner {message.author.id} revoked "
        f"{', '.join(revoked)} Pro from user {target.id}.",
        flush=True,
    )

    await message.reply(
        f"✅ Removed Pro access from {target.mention}.\n"
        f"**Revoked:** {names}\n"
        f"**Users still holding Pro:** {count_pro_users()}",
        mention_author=False,
    )


async def handle_ask_product(message, product_id, prompt):
    if product_id not in PRODUCTS:
        return

    if not prompt.strip():
        await message.reply(
            "Add your question after the command, for example:\n"
            f"`!veyra {product_id} Explain this topic`",
            mention_author=False,
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
                if tier == "pro"
                else "For Free, focus on concise explanations and small examples."
            )
        ),
        "study": (
            "You are Veyra Study, a patient tutor. Teach concepts clearly, "
            "use examples, and create practice questions when requested. "
            + (
                "For Pro, provide detailed notes and structured revision."
                if tier == "pro"
                else "For Free, keep notes and explanations concise."
            )
        ),
        "research": (
            "You are Veyra Research. Be careful with factual claims, "
            "separate known facts from uncertainty, and never invent "
            "sources or claim you searched the web unless a search tool "
            "actually ran. "
            + (
                "For Pro, prepare structured research reports when "
                "appropriate, and use live search when configured."
                if tier == "pro"
                else "For Free, give a concise answer and state when live "
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
            web_search=(
                product_id == "research" and tier == "pro"
            ),
        )

        chunks = split_answer(answer)
        total = len(chunks)

        for index, chunk in enumerate(chunks):
            title = f"{product['emoji']} {product['name']}"

            if total > 1:
                title += f" · Part {index + 1}/{total}"

            embed = discord.Embed(
                title=title,
                description=chunk,
                color=ICE_BLUE,
            )

            embed.set_footer(
                text=f"{tier.upper()} • VEYRA AI • VOLBASTY STUDIOS"
            )

            if index == 0:
                await reply_message.edit(embed=embed)
            else:
                await message.channel.send(embed=embed)

    except Exception as error:
        print(
            f"[PRODUCT ERROR] {product_id}: "
            f"{type(error).__name__}: {error}",
            flush=True,
        )

        error_embed = discord.Embed(
            title="⚠️ Product request failed",
            description=(
                "Veyra couldn't complete this request. "
                "Please try again later."
            ),
            color=discord.Color.orange(),
        )

        try:
            await reply_message.edit(embed=error_embed)
        except discord.HTTPException:
            await message.channel.send(embed=error_embed)
