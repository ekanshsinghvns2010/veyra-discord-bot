
import discord


ICE_BLUE = discord.Color.from_rgb(42, 164, 255)

PRODUCTS = {
    "code": {
        "name": "Veyra Code Pro",
        "emoji": "💻",
        "tagline": "Build beyond the basics.",
        "description": (
            "Advanced coding assistance for substantial projects."
        ),
        "features": [
            "Multi-file project assistance",
            "Extended debugging and code reviews",
            "Architecture and implementation planning",
        ],
        "free": (
            "Small snippets and examples, up to 30 generated "
            "code lines."
        ),
    },
    "study": {
        "name": "Veyra Study Pro",
        "emoji": "📚",
        "tagline": "Turn difficult topics into clear knowledge.",
        "description": (
            "More comprehensive learning and revision assistance."
        ),
        "features": [
            "Detailed chapter explanations",
            "Structured revision notes",
            "Practice questions and study plans",
        ],
        "free": (
            "Short explanations, basic notes, and practice questions."
        ),
    },
    "research": {
        "name": "Veyra Deep Research",
        "emoji": "🔎",
        "tagline": "Explore beyond the first answer.",
        "description": (
            "Extended research and structured report assistance."
        ),
        "features": [
            "Detailed multi-part reports",
            "Comparisons and evidence organization",
            "Source-based research when search is available",
        ],
        "free": (
            "Concise answers using the model's available knowledge."
        ),
    },
}


def shop_embed(product_id=None, server_name="Your server",
               enabled_features=None):
    enabled_features = enabled_features or set()

    embed = discord.Embed(
        title="❄️ VEYRA AI  /  PREMIUM SHOP",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Intelligence deserves room to grow.**\n"
            "Explore specialized AI capabilities for your server.\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=ICE_BLUE,
    )

    if product_id is None:
        for key, product in PRODUCTS.items():
            status = (
                "✅ ACTIVE"
                if key in enabled_features
                else "🔒 NOT ACTIVATED"
            )
            embed.add_field(
                name=f"{product['emoji']}  {product['name']}",
                value=(
                    f"{product['tagline']}\n"
                    f"{product['description']}\n"
                    f"**Server status:** {status}"
                ),
                inline=False,
            )

        embed.add_field(
            name="🛍️ HOW IT WORKS",
            value=(
                "1. Choose a product from the dropdown.\n"
                "2. Review its features and free-tier limits.\n"
                "3. Follow the official purchase flow when available."
            ),
            inline=False,
        )

        embed.set_footer(
            text="VEYRA AI • Powered by Volbasty Studios"
        )
        return embed

    product = PRODUCTS[product_id]
    status = (
        "✅ ACTIVE ON THIS SERVER"
        if product_id in enabled_features
        else "🔒 NOT YET ACTIVATED"
    )

    embed.title = f"{product['emoji']}  {product['name']}"
    embed.description = (
        f"**{product['tagline']}**\n\n"
        f"{product['description']}\n\n"
        f"**Server:** {server_name}\n"
        f"**Access:** {status}"
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
        name="💠 ACTIVATION",
        value=(
            "Online purchasing is not connected yet. "
            "No payment has been taken and no premium access "
            "has been granted."
        ),
        inline=False,
    )
    embed.set_footer(
        text="VEYRA AI • Built by Volbasty Studios"
    )
    return embed


class ShopSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=product["name"],
                value=key,
                description=product["tagline"][:100],
                emoji=product["emoji"],
            )
            for key, product in PRODUCTS.items()
        ]

        super().__init__(
            placeholder="Explore Veyra's premium products...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if not isinstance(view, ShopView):
            return

        view.selected_product = self.values[0]

        await interaction.response.edit_message(
            embed=shop_embed(
                view.selected_product,
                view.server_name,
                view.enabled_features,
            ),
            view=view,
        )


class ShopView(discord.ui.View):
    def __init__(self, server_name, enabled_features=None):
        super().__init__(timeout=180)

        self.server_name = server_name
        self.enabled_features = enabled_features or set()
        self.selected_product = None

        self.add_item(ShopSelect())

    async def interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        if self.message_owner_id is not None:
            if interaction.user.id != self.message_owner_id:
                await interaction.response.send_message(
                    "This shop session belongs to another user. "
                    "Run `!veyra shop` to open your own.",
                    ephemeral=True,
                )
                return False

        return True

    message_owner_id = None

    @discord.ui.button(
        label="View Product",
        emoji="🔍",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def view_product(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.selected_product is None:
            await interaction.response.send_message(
                "Choose a product from the dropdown first.",
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            embed=shop_embed(
                self.selected_product,
                self.server_name,
                self.enabled_features,
            ),
            view=self,
        )

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
        await interaction.response.edit_message(
            embed=shop_embed(
                server_name=self.server_name,
                enabled_features=self.enabled_features,
            ),
            view=self,
        )

    @discord.ui.button(
        label="Purchase Status",
        emoji="🛡️",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def purchase_status(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_message(
            "Purchases are not connected yet. "
            "Premium access is not activated by this shop preview.",
            ephemeral=True,
        )


async def handle_shop(message, prefix=None):
    if prefix is None:
        prefix = "!veyra"

    if message.guild is None:
        await message.reply(
            "Please open the shop from a server."
        )
        return

    view = ShopView(message.guild.name)
    view.message_owner_id = message.author.id

    await message.reply(
        embed=shop_embed(server_name=message.guild.name),
        view=view,
        mention_author=False,
    )
