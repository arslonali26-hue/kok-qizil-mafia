from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import ensure_user, get_user
from shop import load_shop, shop_main_keyboard
from weapons import resolve_weapon_id, get_weapon, xp_capacity
from achievements import get_user_achievements, ACHIEVEMENTS


def profile_text(user_id: int) -> str:
    ensure_user(user_id)
    user = get_user(user_id) or {}

    pul = int(user.get("pul", 0))
    almas = int(user.get("almas", 0))
    defense_hp = int(user.get("defense_hp", 0))

    inventory = user.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}

    equipped_raw = user.get("equipped_weapon", "pistol")
    equipped_id = resolve_weapon_id(equipped_raw)
    weapon = get_weapon(equipped_id)

    if not weapon:
        equipped_id = "weapon_01"
        weapon = get_weapon(equipped_id)

    weapon_name = weapon.get("name", "🔫 Noma'lum qurol")
    base_damage = int(weapon.get("damage", 0))

    weapon_levels = user.get("weapon_levels", {})
    weapon_xp = user.get("weapon_xp", {})

    if not isinstance(weapon_levels, dict):
        weapon_levels = {}
    if not isinstance(weapon_xp, dict):
        weapon_xp = {}

    level = int(weapon_levels.get(equipped_id, 1))
    level = max(1, min(level, 15))

    xp = int(weapon_xp.get(equipped_id, 0))
    xp = max(0, xp)

    # ⭐ Magazin ko'rsatgan XP — Level 1 sig'imi.
    # Keyingi level sig'imi weapons.py dagi 1.20 o'sish bilan hisoblanadi.
    shop_xp = int(weapon.get("shop_xp", 100))
    required_xp = xp_capacity(level, shop_xp)

    battles = int(
        user.get(
            "battle_count",
            int(user.get("battle_wins", 0)) +
            int(user.get("battle_losses", 0))
        )
    )
    wins = int(user.get("battle_wins", user.get("wins", 0)))
    losses = int(user.get("battle_losses", user.get("losses", 0)))
    damage = int(user.get("battle_damage", 0))

    achievements = get_user_achievements(user)
    achievement_total = len(ACHIEVEMENTS)
    achievement_unlocked = len(achievements)

    try:
        shop = load_shop()
    except Exception:
        shop = {"categories": {}}

    medkit_items = (
        shop.get("categories", {})
        .get("medkits", {})
        .get("items", {})
    )

    defense_items = (
        shop.get("categories", {})
        .get("defense", {})
        .get("items", {})
    )

    medkit_lines = []
    medkit_total = 0

    for item_id, item in medkit_items.items():
        count = int(inventory.get(item_id, 0))
        if count > 0:
            medkit_total += count
            medkit_lines.append(
                f"🩹 {item.get('name', item_id)} ×{count}"
            )

    if not medkit_lines:
        medkit_lines.append("• Hozircha medkit yo‘q.")

    defense_total = 0
    defense_lines = []

    for item_id, item in defense_items.items():
        count = int(inventory.get(item_id, 0))
        if count > 0:
            defense_total += count
            defense_lines.append(
                f"🛡️ {item.get('name', item_id)} ×{count}"
            )

    if not defense_lines:
        defense_lines.append("• Hozircha himoya buyumi yo‘q.")

    return (
        "👤 PROFIL\n"
        "━━━━━━━━━━━━━━\n"
        f"🆔 ID: {user_id}\n"
        f"💰 Pul: {pul:,} so‘m\n"
        f"💎 Almas: {almas:,}\n\n"

        "🔫 QUROL\n"
        f"🎯 Jihozlangan: {weapon_name}\n"
        f"💥 Bazaviy zarar: {base_damage}\n"
        f"⭐ Level: {level}/15\n"
        f"✨ XP: {xp}/{required_xp}\n\n"

        "🛡️ HIMOYA\n"
        f"🛡️ Himoya HP: {defense_hp}\n"
        f"📦 Himoya buyumlari: {defense_total} dona\n"
        + "\n".join(defense_lines)
        + "\n\n"

        "🩹 APTECHKA\n"
        f"🎒 Jami: {medkit_total} dona\n"
        + "\n".join(medkit_lines)
        + "\n\n"

        "🏆 STATISTIKA\n"
        f"⚔️ Janglar: {battles}\n"
        f"🏆 G‘alabalar: {wins}\n"
        f"💀 Mag‘lubiyatlar: {losses}\n"
        f"💥 Jami zarar: {damage}\n"
        f"🏅 Achievementlar: {achievement_unlocked}/{achievement_total}"
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔷 ➕ Almas qo‘shish",
                callback_data="profile_topup:almas",
            ),
            InlineKeyboardButton(
                "🪙 ➕ Pul qo‘shish",
                callback_data="profile_topup:pul",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Yangilash",
                callback_data="profile_refresh",
            )
        ],
        [InlineKeyboardButton("🛒 Magazin", callback_data="profile_shop")],
    ])


async def profile_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not user:
        return

    await update.message.reply_text(
        profile_text(user.id),
        reply_markup=profile_keyboard(),
    )


async def profile_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "profile_shop":
        await query.edit_message_text("🛒 MAGAZIN\n━━━━━━━━━━━━━━\nKerakli bo‘limni tanlang:", reply_markup=shop_main_keyboard())
        return
    await query.edit_message_text(
        profile_text(user_id),
        reply_markup=profile_keyboard(),
    )
