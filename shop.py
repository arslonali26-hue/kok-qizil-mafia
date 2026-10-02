import json
import os
import shlex

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import load_data, save_data, ensure_user, get_user, is_admin
from effects import EFFECT_TYPES, create_effect, describe_effects, apply_effects


SHOP_FILE = os.path.join(
    os.path.dirname(__file__),
    "data",
    "shop.json",
)


DEFAULT_SHOP = {
    "categories": {
        "weapons": {
            "name": "🔫 Qurollar",
            "items": {}
        },
        "medkits": {
            "name": "💊 Aptechka",
            "items": {}
        },
        "defense": {
            "name": "🛡 Himoya",
            "items": {}
        },
        "hp": {
            "name": "❤️ HP",
            "items": {}
        },
        "other": {
            "name": "📦 Boshqa",
            "items": {}
        }
    }
}


def load_shop():
    os.makedirs(os.path.dirname(SHOP_FILE), exist_ok=True)

    if not os.path.exists(SHOP_FILE):
        save_shop(DEFAULT_SHOP)
        return DEFAULT_SHOP.copy()

    try:
        with open(SHOP_FILE, "r", encoding="utf-8") as f:
            shop = json.load(f)
    except (json.JSONDecodeError, OSError):
        shop = {}

    if not isinstance(shop, dict):
        shop = {}

    shop.setdefault("categories", {})

    for key, value in DEFAULT_SHOP["categories"].items():
        shop["categories"].setdefault(
            key,
            {
                "name": value["name"],
                "items": {}
            }
        )

    for category in shop["categories"].values():
        for item in category.get("items", {}).values():
            item.setdefault("price", 0)
            item.setdefault("currency", "")
            item.setdefault("description", "")
            item.setdefault("stock", -1)
            item.setdefault("effects", [])

    return shop


def save_shop(shop):
    os.makedirs(os.path.dirname(SHOP_FILE), exist_ok=True)

    temp_file = SHOP_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            shop,
            f,
            ensure_ascii=False,
            indent=4,
        )

    os.replace(temp_file, SHOP_FILE)


def price_text(item):
    price = int(item.get("price", 0))

    if price <= 0:
        return "💰 Narx belgilanmagan"

    currency = item.get("currency", "")

    if currency == "Pul":
        return f"💰 {price:,} so‘m"

    if currency == "Almas":
        return f"💎 {price:,} Almas"

    return "💰 Narx belgilanmagan"


def shop_main_keyboard():
    shop = load_shop()

    rows = []

    for category_id, category in shop["categories"].items():
        rows.append([
            InlineKeyboardButton(
                category.get("name", category_id),
                callback_data=f"shop_category:{category_id}",
            )
        ])

    return InlineKeyboardMarkup(rows)


def shop_category_keyboard(category_id):
    shop = load_shop()
    category = shop["categories"].get(category_id)

    if not category:
        return shop_main_keyboard()

    rows = []

    for item_id, item in category.get("items", {}).items():
        rows.append([
            InlineKeyboardButton(
                f"🛒 {item['name']} — {item['price']:,} {item['currency']}",
                callback_data=f"shop_item:{category_id}:{item_id}",
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Magazin",
            callback_data="shop_back",
        )
    ])

    return InlineKeyboardMarkup(rows)


def shop_item_keyboard(category_id, item_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 Sotib olish",
                callback_data=f"shop_buy:{category_id}:{item_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Orqaga",
                callback_data=f"shop_category:{category_id}",
            )
        ],
    ])


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user.id)

    await update.message.reply_text(
        "🛒 MAGAZIN\n"
        "━━━━━━━━━━━━━━\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=shop_main_keyboard(),
    )


async def shop_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    print(f"🛒 SHOP CALLBACK: {query.data}", flush=True)
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "shop_back":
        await query.edit_message_text(
            "🛒 MAGAZIN\n"
            "━━━━━━━━━━━━━━\n"
            "Kerakli bo‘limni tanlang:",
            reply_markup=shop_main_keyboard(),
        )
        return

    if data.startswith("shop_category:"):
        category_id = data.split(":", 1)[1]

        shop = load_shop()
        category = shop["categories"].get(category_id)

        if not category:
            await query.answer(
                "❌ Bu bo‘lim topilmadi.",
                show_alert=True,
            )
            return

        if not category.get("items"):
            await query.edit_message_text(
                f"{category['name']}\n\n"
                "📦 Hozircha mahsulot yo‘q.",
                reply_markup=shop_category_keyboard(category_id),
            )
            return

        await query.edit_message_text(
            f"{category['name']}\n"
            "━━━━━━━━━━━━━━\n"
            "Mahsulotni tanlang:",
            reply_markup=shop_category_keyboard(category_id),
        )
        return

    if data.startswith("shop_item:"):
        _, category_id, item_id = data.split(":", 2)

        shop = load_shop()
        item = (
            shop["categories"]
            .get(category_id, {})
            .get("items", {})
            .get(item_id)
        )

        if not item:
            await query.answer(
                "❌ Mahsulot topilmadi.",
                show_alert=True,
            )
            return

        description = item.get(
            "description",
            "Tavsif mavjud emas."
        )

        effects_list = item.get("effects", [])
        effect_lines = describe_effects(effects_list)

        effects_text = ""
        if effect_lines:
            effects_text = (
                "\n\n⚙️ EFFEKTLAR\n"
                + "\n".join(f"• {line}" for line in effect_lines)
            )

        text = (
            f"🛒 {item['name']}\n"
            "━━━━━━━━━━━━━━\n"
            f"💰 Narx: {item['price']:,} {item['currency']}\n"
            f"📦 Miqdor: {item.get('stock', -1) if item.get('stock', -1) >= 0 else '♾️'}\n\n"
            f"📝 {description}"
            f"{effects_text}"
        )

        await query.edit_message_text(
            text,
            reply_markup=shop_item_keyboard(
                category_id,
                item_id,
            ),
        )
        return

    if data.startswith("shop_use:"):
        _, category_id, item_id = data.split(":", 2)

        shop = load_shop()

        category = shop["categories"].get(category_id, {})
        item = category.get("items", {}).get(item_id)

        if not item:
            await query.answer(
                "❌ Mahsulot topilmadi.",
                show_alert=True,
            )
            return

        user = get_user(user_id)

        if not user:
            ensure_user(user_id)
            user = get_user(user_id)

        inventory = user.setdefault("inventory", {})
        count = int(inventory.get(item_id, 0))

        if count <= 0:
            await query.answer(
                "❌ Bu mahsulot inventarda yo‘q.",
                show_alert=True,
            )
            return

        effects_list = item.get("effects", [])

        if not effects_list:
            await query.answer(
                "⚠️ Bu mahsulotda hali ishlaydigan effekt yo‘q.",
                show_alert=True,
            )
            return

        messages = apply_effects(user, effects_list)

        if not messages:
            await query.answer(
                "⚠️ Effekt bajarilmadi.",
                show_alert=True,
            )
            return

        inventory[item_id] = count - 1

        if inventory[item_id] <= 0:
            inventory.pop(item_id, None)

        data_all = load_data()
        data_all["users"][str(user_id)] = user
        save_data(data_all)

        await query.answer(
            "✅ Mahsulot ishlatildi!",
            show_alert=True,
        )

        result_text = "\n".join(
            f"• {message}"
            for message in messages
        )

        remaining = int(
            inventory.get(item_id, 0)
        )

        await query.edit_message_text(
            "✅ MAHSULOT ISHLATILDI\n"
            "━━━━━━━━━━━━━━\n"
            f"📦 {item.get('name', 'Nomsiz')}\n\n"
            f"{result_text}\n\n"
            f"🎒 Qoldi: {remaining} dona",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛒 Magazin",
                        callback_data="shop_back",
                    )
                ]
            ]),
        )
        return

    if data.startswith("shop_buy:"):
        _, category_id, item_id = data.split(":", 2)

        shop = load_shop()

        category = shop["categories"].get(category_id, {})
        item = category.get("items", {}).get(item_id)

        if not item:
            await query.answer(
                "❌ Mahsulot topilmadi.",
                show_alert=True,
            )
            return

        stock = int(item.get("stock", -1))

        if stock == 0:
            await query.answer(
                "❌ Mahsulot tugagan.",
                show_alert=True,
            )
            return

        user = get_user(user_id)

        if not user:
            ensure_user(user_id)
            user = get_user(user_id)

        currency = item.get("currency", "Pul")
        price = int(item.get("price", 0))

        if currency == "Pul":
            balance = int(user.get("pul", 0))

            if balance < price:
                await query.answer(
                    f"❌ Pul yetarli emas.\n"
                    f"Kerak: {price:,} Pul\n"
                    f"Sizda: {balance:,} Pul",
                    show_alert=True,
                )
                return

            user["pul"] = balance - price

        elif currency == "Almas":
            balance = int(user.get("almas", 0))

            if balance < price:
                await query.answer(
                    f"❌ Almas yetarli emas.\n"
                    f"Kerak: {price:,} Almas\n"
                    f"Sizda: {balance:,} Almas",
                    show_alert=True,
                )
                return

            user["almas"] = balance - price

        else:
            await query.answer(
                "❌ Valyuta sozlamasi noto‘g‘ri.",
                show_alert=True,
            )
            return

        inventory = user.setdefault("inventory", {})

        inventory[item_id] = int(
            inventory.get(item_id, 0)
        ) + 1

        if stock > 0:
            item["stock"] = stock - 1

        data_all = load_data()
        data_all["users"][str(user_id)] = user
        save_data(data_all)
        save_shop(shop)

        await query.answer(
            f"✅ {item['name']} sotib olindi!",
            show_alert=True,
        )

        await query.edit_message_text(
            f"✅ Xarid muvaffaqiyatli!\n\n"
            f"🛒 {item['name']}\n"
            f"💰 {price:,} {currency} to‘landi.\n"
            f"📦 Inventar: {inventory[item_id]} dona",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "▶️ Ishlatish",
                        callback_data=f"shop_use:{category_id}:{item_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Magazin",
                        callback_data="shop_back",
                    )
                ]
            ]),
        )
        return


async def shop_add_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ Sizda ruxsat yo‘q."
        )
        return

    raw = update.message.text.partition(" ")[2].strip()

    if not raw:
        await update.message.reply_text(
            "🛒 Mahsulot qo‘shish:\n\n"
            "/shopadd category item_id price currency \"Nom\" \"Tavsif\"\n\n"
            "Misol:\n"
            "/shopadd weapons barret 5000 Pul "
            "\"20. Barret .50 Cal Snayper\" "
            "\"Uzoq masofali qurol\""
        )
        return

    try:
        parts = shlex.split(raw)
    except ValueError:
        await update.message.reply_text(
            "❌ Buyruq formati noto‘g‘ri."
        )
        return

    if len(parts) < 6:
        await update.message.reply_text(
            "❌ Yetarli ma’lumot yo‘q.\n\n"
            "Format:\n"
            "/shopadd category item_id price currency \"Nom\" \"Tavsif\""
        )
        return

    category_id = parts[0]
    item_id = parts[1]

    try:
        price = int(parts[2])
    except ValueError:
        await update.message.reply_text(
            "❌ Narx raqam bo‘lishi kerak."
        )
        return

    currency = parts[3]

    if currency not in ("Pul", "Almas"):
        await update.message.reply_text(
            "❌ Valyuta faqat Pul yoki Almas bo‘lishi mumkin."
        )
        return

    name = parts[4]
    description = parts[5]

    shop = load_shop()

    if category_id not in shop["categories"]:
        shop["categories"][category_id] = {
            "name": f"📦 {category_id}",
            "items": {}
        }

    shop["categories"][category_id]["items"][item_id] = {
        "name": name,
        "price": price,
        "currency": currency,
        "description": description,
        "stock": -1,
    }

    save_shop(shop)

    await update.message.reply_text(
        "✅ MAHSULOT QO‘SHILDI\n\n"
        f"📦 Bo‘lim: {category_id}\n"
        f"🆔 ID: {item_id}\n"
        f"🛒 Nomi: {name}\n"
        f"💰 Narxi: {price:,} {currency}\n"
        "♾️ Zaxira: cheksiz"
    )


async def shop_delete_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ Sizda ruxsat yo‘q."
        )
        return

    args = context.args

    if len(args) != 2:
        await update.message.reply_text(
            "Format:\n"
            "/shopdel category item_id\n\n"
            "Misol:\n"
            "/shopdel weapons barret"
        )
        return

    category_id, item_id = args

    shop = load_shop()

    category = shop["categories"].get(category_id)

    if not category or item_id not in category.get("items", {}):
        await update.message.reply_text(
            "❌ Mahsulot topilmadi."
        )
        return

    del category["items"][item_id]
    save_shop(shop)

    await update.message.reply_text(
        f"✅ Mahsulot o‘chirildi:\n"
        f"📦 {category_id}\n"
        f"🆔 {item_id}"
    )


async def shop_price_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ Sizda ruxsat yo‘q."
        )
        return

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(
            "Format:\n"
            "/shopprice category item_id price"
        )
        return

    category_id, item_id, new_price_raw = args

    try:
        new_price = int(new_price_raw)
    except ValueError:
        await update.message.reply_text(
            "❌ Narx raqam bo‘lishi kerak."
        )
        return

    shop = load_shop()

    category = shop["categories"].get(category_id)

    if not category or item_id not in category.get("items", {}):
        await update.message.reply_text(
            "❌ Mahsulot topilmadi."
        )
        return

    category["items"][item_id]["price"] = new_price

    save_shop(shop)

    await update.message.reply_text(
        f"✅ Narx o‘zgartirildi:\n"
        f"🛒 {category['items'][item_id]['name']}\n"
        f"💰 Yangi narx: {new_price:,}"
    )

# ============================================================
# 🛒 ADMIN MAGAZIN BOSHQARUVI — 2-QISM
# ============================================================

def admin_shop_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔫 Qurollar",
                callback_data="admin_shop_cat:weapons"
            )
        ],
        [
            InlineKeyboardButton(
                "💊 Aptechka",
                callback_data="admin_shop_cat:medkits"
            )
        ],
        [
            InlineKeyboardButton(
                "🛡 Himoya",
                callback_data="admin_shop_cat:defense"
            )
        ],
        [
            InlineKeyboardButton(
                "❤️ HP",
                callback_data="admin_shop_cat:hp"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 Boshqa",
                callback_data="admin_shop_cat:other"
            )
        ],
    ])


def admin_shop_category_keyboard(category_id):
    shop = load_shop()
    category = shop["categories"].get(category_id)

    rows = []

    if category:
        for number, (item_id, item) in enumerate(
            category.get("items", {}).items(),
            1
        ):
            rows.append([
                InlineKeyboardButton(
                    f"{number}. {item.get('name', 'Nomsiz')}",
                    callback_data=f"admin_shop_item:{category_id}:{item_id}"
                )
            ])

    rows.append([
        InlineKeyboardButton(
            "➕ Tovar qo‘shish",
            callback_data=f"admin_shop_add:{category_id}"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Magazin boshqaruvi",
            callback_data="admin_shop"
        )
    ])

    return InlineKeyboardMarkup(rows)


def admin_shop_item_keyboard(category_id, item_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 Pul narxi",
                callback_data=(
                    f"admin_shop_currency:"
                    f"{category_id}:{item_id}:Pul"
                )
            ),
            InlineKeyboardButton(
                "💎 Almas narxi",
                callback_data=(
                    f"admin_shop_currency:"
                    f"{category_id}:{item_id}:Almas"
                )
            ),
        ],
        [
            InlineKeyboardButton(
                "⚙️ Effektlar",
                callback_data=(
                    f"admin_shop_effects:"
                    f"{category_id}:{item_id}"
                )
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Tovarni o‘chirish",
                callback_data=(
                    f"admin_shop_delete:"
                    f"{category_id}:{item_id}"
                )
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Orqaga",
                callback_data=f"admin_shop_cat:{category_id}"
            )
        ],
    ])


def admin_shop_category_text(category_id):
    shop = load_shop()
    category = shop["categories"].get(category_id)

    if not category:
        return "❌ Bo‘lim topilmadi."

    lines = [
        f"{category['name']} — 🛒 BOSHQARUV",
        "━━━━━━━━━━━━━━",
    ]

    items = category.get("items", {})

    if not items:
        lines.append("📦 Hozircha tovar yo‘q.")
    else:
        for number, item in enumerate(items.values(), 1):
            lines.append(
                f"{number}. {item.get('name', 'Nomsiz')} — "
                f"{price_text(item)}"
            )

    return "\n".join(lines)



# ============================================================
# ⚙️ ADMIN — TOVAR EFFEKT BOSHQARUVI
# ============================================================

def admin_shop_effects_keyboard(category_id, item_id):
    shop = load_shop()

    category = shop["categories"].get(category_id, {})
    item = category.get("items", {}).get(item_id)

    rows = []

    if not item:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Orqaga",
                    callback_data=f"admin_shop_cat:{category_id}"
                )
            ]
        ])

    effects = item.get("effects", [])

    for index, effect in enumerate(effects, 1):
        descriptions = describe_effects([effect])

        text = (
            descriptions[0]
            if descriptions
            else "⚙️ Noma’lum effekt"
        )

        rows.append([
            InlineKeyboardButton(
                f"🗑 {index}. {text}",
                callback_data=(
                    f"admin_shop_effect_delete:"
                    f"{category_id}:{item_id}:{index - 1}"
                )
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "➕ Effekt qo‘shish",
            callback_data=(
                f"admin_shop_effect_add_menu:"
                f"{category_id}:{item_id}"
            )
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Tovar",
            callback_data=(
                f"admin_shop_item:{category_id}:{item_id}"
            )
        )
    ])

    return InlineKeyboardMarkup(rows)


def admin_shop_effect_text(category_id, item_id):
    shop = load_shop()

    category = shop["categories"].get(category_id, {})
    item = category.get("items", {}).get(item_id)

    if not item:
        return "❌ Tovar topilmadi."

    lines = [
        "⚙️ EFFEKTLAR",
        "━━━━━━━━━━━━━━",
        f"📦 {item.get('name', 'Nomsiz')}",
        "",
    ]

    effects = item.get("effects", [])

    if not effects:
        lines.append("📭 Hozircha effekt yo‘q.")
    else:
        for index, effect in enumerate(effects, 1):
            descriptions = describe_effects([effect])

            text = (
                descriptions[0]
                if descriptions
                else "⚙️ Noma’lum effekt"
            )

            lines.append(
                f"{index}. {text}"
            )

    return "\n".join(lines)


def admin_shop_effect_add_keyboard(
    category_id,
    item_id,
):
    rows = []

    for effect_id, info in EFFECT_TYPES.items():
        rows.append([
            InlineKeyboardButton(
                info["name"],
                callback_data=(
                    f"admin_shop_effect_add:"
                    f"{category_id}:{item_id}:{effect_id}"
                )
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Tovar",
            callback_data=(
                f"admin_shop_item:{category_id}:{item_id}"
            )
        )
    ])

    return InlineKeyboardMarkup(rows)


async def admin_shop_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    print(f"🛒 SHOP CALLBACK: {query.data}", flush=True)
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer(
            "⛔ Ruxsat yo‘q.",
            show_alert=True
        )
        return

    await query.answer()
    data = query.data

    if data == "admin_shop":
        await query.edit_message_text(
            "🛒 MAGAZIN BOSHQARUVI\n"
            "━━━━━━━━━━━━━━\n"
            "Bo‘limni tanlang:",
            reply_markup=admin_shop_keyboard()
        )
        return

    if data.startswith("admin_shop_cat:"):
        category_id = data.split(":", 1)[1]

        await query.edit_message_text(
            admin_shop_category_text(category_id),
            reply_markup=admin_shop_category_keyboard(
                category_id
            )
        )
        return

    if data.startswith("admin_shop_add:"):
        category_id = data.split(":", 1)[1]

        context.user_data["admin_shop_state"] = "add_product"
        context.user_data["admin_shop_category"] = category_id

        shop = load_shop()
        category = shop["categories"].get(category_id, {})

        await query.message.reply_text(
            f"➕ {category.get('name', 'Bo‘lim')}ga tovar qo‘shish\n\n"
            "📝 Faqat tovar nomini yuboring.\n\n"
            "Masalan:\n"
            "🎯 Barret .50 Cal Snayper"
        )
        return

    if data.startswith("admin_shop_item:"):
        _, category_id, item_id = data.split(":", 2)

        shop = load_shop()

        item = (
            shop["categories"]
            .get(category_id, {})
            .get("items", {})
            .get(item_id)
        )

        if not item:
            await query.answer(
                "❌ Tovar topilmadi.",
                show_alert=True
            )
            return

        await query.edit_message_text(
            "🛒 TOVAR BOSHQARUVI\n"
            "━━━━━━━━━━━━━━\n"
            f"📦 {item.get('name', 'Nomsiz')}\n"
            f"{price_text(item)}\n\n"
            "Narx valyutasini tanlang:",
            reply_markup=admin_shop_item_keyboard(
                category_id,
                item_id
            )
        )
        return

    # ⚙️ EFFEKT MENYUSI
    if data.startswith("admin_shop_effects:"):
        _, category_id, item_id = data.split(":", 2)

        await query.edit_message_text(
            admin_shop_effect_text(
                category_id,
                item_id,
            ),
            reply_markup=admin_shop_effects_keyboard(
                category_id,
                item_id,
            ),
        )
        return

    # ➕ EFFEKT TURINI TANLASH
    if data.startswith("admin_shop_effect_add_menu:"):
        _, category_id, item_id = data.split(":", 2)

        await query.edit_message_text(
            "⚙️ EFFEKT TURINI TANLANG\n"
            "━━━━━━━━━━━━━━\n"
            "📦 Tovarga nima qilishini tanlang:",
            reply_markup=admin_shop_effect_add_keyboard(
                category_id,
                item_id,
            ),
        )
        return

    # ➕ EFFEKT TANLANDI
    if data.startswith("admin_shop_effect_add:"):
        _, category_id, item_id, effect_type = data.split(":", 3)

        if effect_type not in EFFECT_TYPES:
            await query.answer(
                "❌ Effekt turi topilmadi.",
                show_alert=True,
            )
            return

        context.user_data["admin_shop_state"] = "effect_value"
        context.user_data["admin_shop_category"] = category_id
        context.user_data["admin_shop_item"] = item_id
        context.user_data["admin_shop_effect_type"] = effect_type

        effect_name = EFFECT_TYPES[effect_type]["name"]

        await query.message.reply_text(
            f"{effect_name}\n\n"
            "🔢 Effekt qiymatini raqam bilan yuboring.\n\n"
            "Masalan:\n"
            "100\n\n"
            "🩹 Keyingi davolash × uchun:\n"
            "2 = 2 baravar\n"
            "3 = 3 baravar",
        )
        return

    # 🗑 EFFEKT O‘CHIRISH
    if data.startswith("admin_shop_effect_delete:"):
        _, category_id, item_id, index_text = data.split(":", 3)

        try:
            index = int(index_text)
        except ValueError:
            await query.answer(
                "❌ Effekt raqami xato.",
                show_alert=True,
            )
            return

        shop = load_shop()
        category = shop["categories"].get(category_id)

        if not category:
            await query.answer(
                "❌ Bo‘lim topilmadi.",
                show_alert=True,
            )
            return

        item = category.get("items", {}).get(item_id)

        if not item:
            await query.answer(
                "❌ Tovar topilmadi.",
                show_alert=True,
            )
            return

        effects = item.setdefault("effects", [])

        if index < 0 or index >= len(effects):
            await query.answer(
                "❌ Effekt topilmadi.",
                show_alert=True,
            )
            return

        removed = effects.pop(index)
        save_shop(shop)

        removed_text = describe_effects([removed])

        text = (
            removed_text[0]
            if removed_text
            else "⚙️ Effekt"
        )

        await query.edit_message_text(
            f"🗑 EFFEKT O‘CHIRILDI\n\n"
            f"❌ {text}\n\n"
            f"{admin_shop_effect_text(category_id, item_id)}",
            reply_markup=admin_shop_effects_keyboard(
                category_id,
                item_id,
            ),
        )
        return

    if data.startswith("admin_shop_currency:"):
        _, category_id, item_id, currency = data.split(":", 3)

        context.user_data["admin_shop_state"] = "set_price"
        context.user_data["admin_shop_category"] = category_id
        context.user_data["admin_shop_item"] = item_id
        context.user_data["admin_shop_currency"] = currency

        symbol = "💰 Pul" if currency == "Pul" else "💎 Almas"

        await query.message.reply_text(
            f"{symbol}\n\n"
            "💵 Narxni raqam bilan yuboring.\n\n"
            "Masalan:\n"
            "5000"
        )
        return

    if data.startswith("admin_shop_delete:"):
        _, category_id, item_id = data.split(":", 2)

        shop = load_shop()
        category = shop["categories"].get(category_id)

        if not category:
            await query.answer(
                "❌ Bo‘lim topilmadi.",
                show_alert=True
            )
            return

        items = category.get("items", {})
        item = items.get(item_id)

        if not item:
            await query.answer(
                "❌ Tovar topilmadi.",
                show_alert=True
            )
            return

        name = item.get("name", "Nomsiz")
        del items[item_id]

        save_shop(shop)

        await query.edit_message_text(
            "✅ TOVAR O‘CHIRILDI\n\n"
            f"📦 {name}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Bo‘limga qaytish",
                        callback_data=f"admin_shop_cat:{category_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🛒 Magazin boshqaruvi",
                        callback_data="admin_shop"
                    )
                ],
            ])
        )
        return


async def admin_shop_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    user = update.effective_user

    if not is_admin(user.id):
        return

    state = context.user_data.get("admin_shop_state")

    # ➕ TOVAR QO‘SHISH
    if state == "add_product":
        name = update.message.text.strip()

        if not name:
            await update.message.reply_text(
                "❌ Tovar nomi bo‘sh bo‘lishi mumkin emas."
            )
            return

        category_id = context.user_data.get(
            "admin_shop_category"
        )

        shop = load_shop()
        category = shop["categories"].get(category_id)

        if not category:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Bo‘lim topilmadi."
            )
            return

        items = category.setdefault("items", {})

        number = len(items) + 1
        item_id = f"item_{number}"

        while item_id in items:
            number += 1
            item_id = f"item_{number}"

        items[item_id] = {
            "name": name,
            "price": 0,
            "currency": "",
            "description": "",
            "stock": -1,
        }

        save_shop(shop)

        context.user_data.pop("admin_shop_state", None)
        context.user_data.pop("admin_shop_category", None)

        await update.message.reply_text(
            "✅ TOVAR QO‘SHILDI\n\n"
            f"📦 {name}\n"
            "💰 Narx: belgilanmagan\n\n"
            "Endi shu tovarni tanlab "
            "💰 Pul yoki 💎 Almas narxini belgilang."
        )
        return

    # ⚙️ EFFEKT QIYMATINI KIRITISH
    if state == "effect_value":
        raw = update.message.text.strip()
        raw = raw.replace(",", "").replace(" ", "")

        try:
            value = float(raw)
        except ValueError:
            await update.message.reply_text(
                "❌ Effekt qiymati faqat raqam bo‘lishi kerak.\n\n"
                "Masalan:\n"
                "100\n"
                "2\n"
                "500"
            )
            return

        if value < 0:
            await update.message.reply_text(
                "❌ Effekt qiymati manfiy bo‘lishi mumkin emas."
            )
            return

        if value.is_integer():
            value = int(value)

        category_id = context.user_data.get(
            "admin_shop_category"
        )

        item_id = context.user_data.get(
            "admin_shop_item"
        )

        effect_type = context.user_data.get(
            "admin_shop_effect_type"
        )

        if not category_id or not item_id:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Effekt ma’lumotlari topilmadi."
            )
            return

        if effect_type not in EFFECT_TYPES:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Effekt turi topilmadi."
            )
            return

        shop = load_shop()

        category = shop["categories"].get(
            category_id
        )

        item = (
            category.get("items", {}).get(item_id)
            if category
            else None
        )

        if not item:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Tovar topilmadi."
            )
            return

        effect = create_effect(
            effect_type,
            value,
        )

        item.setdefault(
            "effects",
            []
        ).append(effect)

        save_shop(shop)

        effect_text = describe_effects(
            [effect]
        )

        saved_text = (
            effect_text[0]
            if effect_text
            else "⚙️ Effekt"
        )

        name = item.get(
            "name",
            "Nomsiz"
        )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ EFFEKT SAQLANDI\n\n"
            f"📦 {name}\n"
            f"⚙️ {saved_text}\n\n"
            "Endi bu effekt tovar tarkibida saqlanadi."
        )
        return

    # 💰 NARX KIRITISH
    if state == "set_price":
        raw = update.message.text.strip()
        raw = raw.replace(",", "").replace(" ", "")

        try:
            price = int(raw)
        except ValueError:
            await update.message.reply_text(
                "❌ Narx faqat raqam bo‘lishi kerak.\n\n"
                "Masalan: 5000"
            )
            return

        if price <= 0:
            await update.message.reply_text(
                "❌ Narx 0 dan katta bo‘lishi kerak."
            )
            return

        category_id = context.user_data.get(
            "admin_shop_category"
        )
        item_id = context.user_data.get(
            "admin_shop_item"
        )
        currency = context.user_data.get(
            "admin_shop_currency"
        )

        if currency not in ("Pul", "Almas"):
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Valyuta tanlashda xato."
            )
            return

        shop = load_shop()

        category = shop["categories"].get(category_id)
        item = (
            category.get("items", {}).get(item_id)
            if category
            else None
        )

        if not item:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Tovar topilmadi."
            )
            return

        item["price"] = price
        item["currency"] = currency

        save_shop(shop)

        name = item.get("name", "Nomsiz")

        context.user_data.clear()

        await update.message.reply_text(
            "✅ NARX SAQLANDI\n\n"
            f"🛒 {name}\n"
            f"{price_text(item)}"
        )
        return

# ============================================================
# 🛒 ADMIN MAGAZIN BOSHQARUVI — 2-QISM
# ============================================================

def admin_shop_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔫 Qurollar",
                callback_data="admin_shop_cat:weapons"
            )
        ],
        [
            InlineKeyboardButton(
                "💊 Aptechka",
                callback_data="admin_shop_cat:medkits"
            )
        ],
        [
            InlineKeyboardButton(
                "🛡 Himoya",
                callback_data="admin_shop_cat:defense"
            )
        ],
        [
            InlineKeyboardButton(
                "❤️ HP",
                callback_data="admin_shop_cat:hp"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 Boshqa",
                callback_data="admin_shop_cat:other"
            )
        ],
    ])


def admin_shop_category_keyboard(category_id):
    shop = load_shop()
    category = shop["categories"].get(category_id)

    rows = []

    if category:
        for number, (item_id, item) in enumerate(
            category.get("items", {}).items(),
            1
        ):
            rows.append([
                InlineKeyboardButton(
                    f"{number}. {item.get('name', 'Nomsiz')}",
                    callback_data=f"admin_shop_item:{category_id}:{item_id}"
                )
            ])

    rows.append([
        InlineKeyboardButton(
            "➕ Tovar qo‘shish",
            callback_data=f"admin_shop_add:{category_id}"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Magazin boshqaruvi",
            callback_data="admin_shop"
        )
    ])

    return InlineKeyboardMarkup(rows)


def admin_shop_category_text(category_id):
    shop = load_shop()
    category = shop["categories"].get(category_id)

    if not category:
        return "❌ Bo‘lim topilmadi."

    lines = [
        f"{category['name']} — 🛒 BOSHQARUV",
        "━━━━━━━━━━━━━━",
    ]

    items = category.get("items", {})

    if not items:
        lines.append("📦 Hozircha tovar yo‘q.")
    else:
        for number, item in enumerate(items.values(), 1):
            lines.append(
                f"{number}. {item.get('name', 'Nomsiz')} — "
                f"{price_text(item)}"
            )

    return "\n".join(lines)
