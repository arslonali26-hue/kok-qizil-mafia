import json
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import ensure_user, get_user, load_data, save_data
from shop import load_shop


def inventory_keyboard(user_id):
    user = get_user(user_id) or {}
    inventory = user.get("inventory", {})

    rows = []

    for category_id, title, emoji in (
        ("weapons", "🔫 Qurollar", "🔫"),
        ("medkits", "🩹 Medkitlar", "🩹"),
        ("defense", "🛡️ Himoya", "🛡️"),
    ):
        items = []
        try:
            shop = load_shop()
            items = shop["categories"].get(category_id, {}).get("items", {})
        except Exception:
            items = {}

        count_found = False

        for item_id, item in items.items():
            count = int(inventory.get(item_id, 0))
            if count <= 0:
                continue

            count_found = True

            if category_id == "weapons":
                rows.append([
                    InlineKeyboardButton(
                        f"{emoji} {item.get('name', item_id)} ×{count}",
                        callback_data=f"inventory_equip:{item_id}",
                    )
                ])

        if not count_found and category_id != "weapons":
            continue

    rows.append([
        InlineKeyboardButton(
            "🛒 Magazin",
            callback_data="shop_back",
        )
    ])

    return InlineKeyboardMarkup(rows)


def inventory_text(user_id):
    ensure_user(user_id)
    user = get_user(user_id) or {}
    inventory = user.get("inventory", {})
    equipped = user.get("equipped_weapon", "pistol")

    try:
        shop = load_shop()
    except Exception:
        shop = {"categories": {}}

    weapon_items = shop.get("categories", {}).get("weapons", {}).get("items", {})
    medkit_items = shop.get("categories", {}).get("medkits", {}).get("items", {})
    defense_items = shop.get("categories", {}).get("defense", {}).get("items", {})

    lines = [
        "🎒 INVENTAR",
        "━━━━━━━━━━━━━━",
        "",
    ]

    equipped_name = equipped

    if equipped in weapon_items:
        equipped_name = weapon_items[equipped].get("name", equipped)

    lines.append(f"🎯 Jihozlangan: {equipped_name}")
    lines.append("")

    lines.append("🔫 QUROLLAR")
    weapon_found = False

    for item_id, item in weapon_items.items():
        count = int(inventory.get(item_id, 0))
        if count > 0:
            marker = " ✅" if item_id == equipped else ""
            lines.append(
                f"• {item.get('name', item_id)} ×{count}{marker}"
            )
            weapon_found = True

    if not weapon_found:
        lines.append("• Hozircha qurol yo‘q.")

    lines.append("")
    lines.append("🩹 MEDKITLAR")
    medkit_found = False

    for item_id, item in medkit_items.items():
        count = int(inventory.get(item_id, 0))
        if count > 0:
            lines.append(
                f"• {item.get('name', item_id)} ×{count}"
            )
            medkit_found = True

    if not medkit_found:
        lines.append("• Hozircha medkit yo‘q.")

    lines.append("")
    lines.append("🛡️ HIMOYA")
    defense_found = False

    for item_id, item in defense_items.items():
        count = int(inventory.get(item_id, 0))
        if count > 0:
            lines.append(
                f"• {item.get('name', item_id)} ×{count}"
            )
            defense_found = True

    if not defense_found:
        lines.append("• Hozircha himoya yo‘q.")

    return "\n".join(lines)


async def inventory_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id
    ensure_user(user_id)

    await update.message.reply_text(
        inventory_text(user_id),
        reply_markup=inventory_keyboard(user_id),
    )


async def inventory_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "inventory_refresh":
        await query.edit_message_text(
            inventory_text(user_id),
            reply_markup=inventory_keyboard(user_id),
        )
        return

    if data.startswith("inventory_equip:"):
        item_id = data.split(":", 1)[1]

        user = get_user(user_id)
        if not user:
            ensure_user(user_id)
            user = get_user(user_id)

        inventory = user.setdefault("inventory", {})
        count = int(inventory.get(item_id, 0))

        if count <= 0:
            await query.answer(
                "❌ Bu qurol inventarda yo‘q.",
                show_alert=True,
            )
            return

        shop = load_shop()
        item = (
            shop.get("categories", {})
            .get("weapons", {})
            .get("items", {})
            .get(item_id)
        )

        if not item:
            await query.answer(
                "❌ Qurol topilmadi.",
                show_alert=True,
            )
            return

        user["equipped_weapon"] = item_id

        data_all = load_data()
        data_all["users"][str(user_id)] = user
        save_data(data_all)

        await query.answer(
            "🔫 Qurol jihozlandi!",
            show_alert=True,
        )

        await query.edit_message_text(
            inventory_text(user_id),
            reply_markup=inventory_keyboard(user_id),
        )
        return
