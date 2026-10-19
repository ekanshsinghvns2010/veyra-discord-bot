
import discord
from pathlib import Path

ICE_BLUE = discord.Color.from_rgb(42, 164, 255)

ASSETS = Path(__file__).resolve().parent.parent / "assets"

PRODUCTS = {
    "code": {
        "name": "Veyra Code Pro",
        "emoji": "💻",
        "tagline": "Build beyond the basics.",
        "price": "₹29",
        "image": "code_pro.png",
        "description": (
            "Advanced coding assistance for substantial projects."
        ),
        "features": [
            "Multi-file project assistance",
            "Extended debugging and code reviews",
            "Architecture and implementation planning",
        ],
        "free": "Small snippets and examples, up to 30 generated code lines.",
    },
    "study": {
        "name": "Veyra Study Pro",
        "emoji": "📚",
        "tagline": "Turn difficult topics into clear knowledge.",
        "price": "₹19",
        "image": "study_pro.png",
        "description": (
            "More comprehensive learning and revision assistance."
        ),
        "features": [
            "Detailed chapter explanations",
            "Structured revision notes",
            "Practice questions and study plans",
        ],
        "free": "Short explanations, basic notes, and practice questions.",
    },
    "research": {
        "name": "Veyra Deep Research",
        "emoji": "🔎",
        "tagline": "Explore beyond the first answer.",
        "price": "₹39",
        "image": "deep_research.png",
        "description": (
            "Extended research and structured report assistance."
        ),
        "features": [
            "Detailed multi-part reports",
            "Comparisons and evidence organization",
            "Source-based research when search is available",
        ],
        "free": "Concise answers using the model's available knowledge.",
    },
}


def get_banner_file():
    path = ASSETS / "shop_banner.gif"
    if not path.is_file():
        return None
    return discord.File(path, filename="shop_banner.gif")


def get_product_file(product_id):
    path = ASSETS / PRODUCTS[product_id]["image"]
    if not path.is_file():
        return None
    return discord.File(path, filename=PRODUCTS[product_id]["image"])


def shop_embed(
    product_id=None,
    server_name="Your server",
    enabled_features=None,
):
    enabled_features = enabled_features or set()

    if product_id is None:
        embed = discord.Embed(
            title="❄️ VEYRA AI  /  PREMIUM SHOP",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "**INTELLIGENCE DESERVES ROOM TO GROW.**\n"
                "Discover specialized AI experiences built for "
                "your creativity, learning, and research.\n\n"
                "👇 **Select a product below to explore it.**\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=ICE_BLUE,
        )

        for key, product in PRODUCTS.items():
            status = (
                "✅ ACTIVE"
                if key in enabled_features
                else "🔒 PREVIEW"
            )
            embed.add_field(
                name=(
                    f"{product['emoji']} {product['name']} "
                    f"— {product['price']}"
                ),
                value=(
                    f"{product['tagline']}\n"
                    f"{status} · One-time price"
                ),
                inline=False,
            )

        embed.add_field(
            name="🛍️ HOW IT WORKS",
            value=(
                "Choose a product from the menu to see its image, "
                "features, price, and free-tier details."
            ),
            inline=False,
        )
        embed.set_footer(
            text="VEYRA AI  •  BY VOLBASTY STUDIOS"
        )
        return embed

    product = PRODUCTS[product_id]
    status = (
        "✅ ACTIVE ON THIS SERVER"
        if product_id in enabled_features
        else "🔒 NOT ACTIVATED"
    )

    embed = discord.Embed(
        title=f"{product['emoji']}  {product['name']}",
        description=(
            f"*{product['tagline']}*\n\n"
            f"{product['description']}\n\n"
            f"## {product['price']} INR\n"
            "**One-time price** · No recurring subscription\n\n"
            f"**Server:** {server_name}\n"
            f"**Status:** {status}"
        ),
        color=ICE_BLUE,
    )

    embed.add_field(
        name="✨ PREMIUM CAPABILITIES",
        value="\n".join(
            f"・{feature}" for feature in product["features"]
        ),
        inline=False,
    )
    embed.add_field(
        name="🆓 FREE TIER",
        value=product["free"],
        inline=False,
    )
    embed.add_field(
        name="💠 PURCHASE & ACTIVATION",
        value=(
            "Purchasing is not available yet. This is a shop "
            "preview; no payment is collected and premium access "
            "is not activated."
        ),
        inline=False,
    )
    embed.set_footer(
        text="VEYRA AI  •  BY VOLBASTY STUDIOS"
    )
    return embed


class ShopSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=product["name"],
                value=key,
                description=(
                    f"{product['price']} one-time · "
                    f"{product['tagline']}"
                )[:100],
                emoji=product["emoji"],
            )
            for key, product in PRODUCTS.items()
        ]

        super().__init__(
            placeholder="Explore Veyra's premium products...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, ShopView):
            return

        product_id = self.values[0]
        view.selected_product = product_id

        product_file = get_product_file(product_id)
        files = [product_file] if product_file else []

        await interaction.response.edit_message(
            content=None,
            embed=shop_embed(
                product_id,
                view.server_name,
                view.enabled_features,
            ),
            attachments=files,
            view=view,
        )


class ShopView(discord.ui.View):
    def __init__(self, server_name, enabled_features=None):
        super().__init__(timeout=180)

        self.server_name = server_name
        self.enabled_features = enabled_features or set()
        self.selected_product = None
        self.message_owner_id = None

        self.add_item(ShopSelect())

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if (
            self.message_owner_id is not None
            and interaction.user.id != self.message_owner_id
        ):
            await interaction.response.send_message(
                "This shop session belongs to another user. "
                "Run `!veyra shop` to open your own.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Shop Home",
        emoji="❄️",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def shop_home(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.selected_product = None
        banner = get_banner_file()
        files = [banner] if banner else []

        await interaction.response.edit_message(
            content=None,
            embed=shop_embed(
                server_name=self.server_name,
                enabled_features=self.enabled_features,
            ),
            attachments=files,
            view=self,
        )

    @discord.ui.button(
        label="Purchase Status",
        emoji="🛡️",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def purchase_status(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_message(
            "🛡️ **Purchase Status**\n"
            "Purchases aren't connected yet. No payment has been "
            "taken, and premium access hasn't been activated.",
            ephemeral=True,
        )


async def handle_shop(message, prefix=None):
    if message.guild is None:
        await message.reply("Please open the shop from a server.")
        return

    view = ShopView(message.guild.name)
    view.message_owner_id = message.author.id

    banner = get_banner_file()
    files = [banner] if banner else []

    embed = shop_embed(server_name=message.guild.name)

    if banner:
        embed.set_image(url="attachment://shop_banner.gif")

    await message.reply(
        embed=embed,
        files=files,
        view=view,
        mention_author=False,
    )
