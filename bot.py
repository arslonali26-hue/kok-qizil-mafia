from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import BOT_TOKEN, MAIN_ADMIN_ID
from database import (
    load_data,
    save_data,
    ensure_user,
    is_admin,
)

def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 Pul berish",
                callback_data="admin_give_pul"
            ),
            InlineKeyboardButton(
                "💎 Almas berish",
                callback_data="admin_give_almas"
            )
        ],
        [
            InlineKeyboardButton(
                "👑 Admin qo‘shish",
                callback_data="admin_add"
            ),
            InlineKeyboardButton(
                "❌ Admin o‘chirish",
                callback_data="admin_remove"
            )
        ],
        [
            InlineKeyboardButton(
                "⚙️ Sozlamalar",
                callback_data="admin_settings"
            )
        ]
    ])


async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ Siz admin emassiz."
        )
        return

    await update.message.reply_text(
        "👑 ADMIN PANEL\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=admin_keyboard()
    )


async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer(
            "⛔ Ruxsat yo‘q.",
            show_alert=True
        )
        return

    data = query.data

    if data == "admin_give_pul":
        context.user_data["admin_action"] = "give_pul"

        await query.message.reply_text(
            "💰 Pul berish.\n\n"
            "Quyidagi formatda yuboring:\n\n"
            "/givepul USER_ID MIQDOR\n\n"
            "Masalan:\n"
            "/givepul 123456789 500"
        )

    elif data == "admin_give_almas":
        context.user_data["admin_action"] = "give_almas"

        await query.message.reply_text(
            "💎 Almas berish.\n\n"
            "Quyidagi formatda yuboring:\n\n"
            "/givealmas USER_ID MIQDOR\n\n"
            "Masalan:\n"
            "/givealmas 123456789 5"
        )

    elif data == "admin_add":
        await query.message.reply_text(
            "👑 Admin qo‘shish:\n\n"
            "/addadmin USER_ID"
        )

    elif data == "admin_remove":
        await query.message.reply_text(
            "❌ Admin o‘chirish:\n\n"
            "/removeadmin USER_ID"
        )

    elif data == "admin_settings":
        settings = load_data()["settings"]

        await query.message.reply_text(
            "⚙️ BOT SOZLAMALARI\n\n"
            f"💰 G‘alaba mukofoti: {settings['win_reward']} Pul\n"
            f"🎁 Jamoa bonusi: {settings['team_bonus']} Pul\n"
            f"💎 Almas streak: {settings['win_streak_for_almas']} g‘alaba\n\n"
            "O‘zgartirish:\n"
            "/setreward MIQDOR\n"
            "/setbonus MIQDOR\n"
            "/setstreak MIQDOR"
        )


async def give_pul(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Format:\n/givepul USER_ID MIQDOR"
        )
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ USER_ID va miqdor raqam bo‘lishi kerak."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ Miqdor 0 dan katta bo‘lishi kerak."
        )
        return

    data = ensure_user(target_id)

    data["users"][str(target_id)]["pul"] += amount

    save_data(data)

    await update.message.reply_text(
        f"✅ Foydalanuvchiga {amount} 💰 Pul berildi.\n\n"
        f"👤 ID: {target_id}"
    )


async def give_almas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Format:\n/givealmas USER_ID MIQDOR"
        )
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ USER_ID va miqdor raqam bo‘lishi kerak."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ Miqdor 0 dan katta bo‘lishi kerak."
        )
        return

    data = ensure_user(target_id)

    data["users"][str(target_id)]["almas"] += amount

    save_data(data)

    await update.message.reply_text(
        f"✅ Foydalanuvchiga {amount} 💎 Almas berildi.\n\n"
        f"👤 ID: {target_id}"
    )


async def add_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id

    if user_id != MAIN_ADMIN_ID:
        await update.message.reply_text(
            "⛔ Faqat bosh admin admin qo‘sha oladi."
        )
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Format:\n/addadmin USER_ID"
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ USER_ID raqam bo‘lishi kerak."
        )
        return

    data = load_data()

    if target_id not in data["admins"]:
        data["admins"].append(target_id)

    save_data(data)

    await update.message.reply_text(
        f"✅ {target_id} admin qilindi."
    )


async def remove_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id

    if user_id != MAIN_ADMIN_ID:
        await update.message.reply_text(
            "⛔ Faqat bosh admin admin o‘chira oladi."
        )
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Format:\n/removeadmin USER_ID"
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ USER_ID raqam bo‘lishi kerak."
        )
        return

    data = load_data()

    if target_id in data["admins"]:
        data["admins"].remove(target_id)

    save_data(data)

    await update.message.reply_text(
        f"✅ {target_id} adminlikdan chiqarildi."
    )


async def set_reward(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != MAIN_ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Format:\n/setreward MIQDOR"
        )
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        return

    data = load_data()
    data["settings"]["win_reward"] = amount
    save_data(data)

    await update.message.reply_text(
        f"✅ G‘alaba mukofoti {amount} Pul bo‘ldi."
    )


async def set_bonus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != MAIN_ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Format:\n/setbonus MIQDOR"
        )
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        return

    data = load_data()
    data["settings"]["team_bonus"] = amount
    save_data(data)

    await update.message.reply_text(
        f"✅ Jamoa bonusi {amount} Pul bo‘ldi."
    )


async def set_streak(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != MAIN_ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Format:\n/setstreak MIQDOR"
        )
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        return

    data = load_data()
    data["settings"]["win_streak_for_almas"] = amount
    save_data(data)

    await update.message.reply_text(
        f"✅ Almas streaki {amount} ta g‘alabaga o‘zgartirildi."
    )
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from game import GAME_ROOMS
from weapons import WEAPONS, resolve_weapon_id


def alive_players(room, side=None):
    result = []

    for user_id in room["players"]:
        if room["hp"].get(user_id, 0) <= 0:
            continue

        if side is not None and room["sides"].get(user_id) != side:
            continue

        result.append(user_id)

    return result


def attack_keyboard(chat_id, attacker_id):
    room = GAME_ROOMS[chat_id]
    attacker_side = room["sides"].get(attacker_id)

    enemy_side = "red" if attacker_side == "blue" else "blue"

    buttons = []

    for user_id in alive_players(room, enemy_side):
        user_info = room.get("users", {}).get(user_id, {})
        player_name = user_info.get("name") or f"O‘yinchi {user_id}"

        buttons.append([
            InlineKeyboardButton(
                f"🎯 {player_name}",
                callback_data=f"attack_target:{user_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Orqaga",
            callback_data="battle_menu"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def battle_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔫 Hujum",
                callback_data="battle_attack"
            ),
            InlineKeyboardButton(
                "🛡 Himoya",
                callback_data="battle_defense"
            ),
        ],
        [
            InlineKeyboardButton(
                "💊 Aptechka",
                callback_data="battle_medkit"
            ),
            InlineKeyboardButton(
                "🔫 Qurol",
                callback_data="battle_weapon"
            ),
        ]
    ])


def weapon_keyboard():
    buttons = []

    for weapon_id, weapon in WEAPONS.items():
        buttons.append([
            InlineKeyboardButton(
                weapon["name"],
                callback_data=f"weapon:{weapon_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Orqaga",
            callback_data="battle_menu"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def battle_text(room, user_id):
    side = room["sides"].get(user_id)

    side_name = "🔵 KO‘K" if side == "blue" else "🔴 QIZIL"

    weapon_id = resolve_weapon_id(room.get("weapon", {}).get(user_id, "pistol"))
    weapon_name = WEAPONS[weapon_id]["name"]

    return (
        f"{side_name}\n\n"
        f"❤️ HP: {room['hp'].get(user_id, 0)}/100\n"
        f"⚡ Energy: {room['energy'].get(user_id, 0)}/100\n"
        f"🔫 Qurol: {weapon_name}\n"
        f"🛡 Himoya: "
        f"{'Ishlatilgan' if room['defense_used'].get(user_id) else 'Mavjud'}\n"
        f"💊 Aptechka: "
        f"{3 - room['medkit_used'].get(user_id, 0)} ta\n\n"
        "Harakatni tanlang:"
    )


def check_winner(chat_id):
    room = GAME_ROOMS[chat_id]

    blue_alive = alive_players(room, "blue")
    red_alive = alive_players(room, "red")

    if not blue_alive and red_alive:
        return "red"

    if not red_alive and blue_alive:
        return "blue"

    return None


def attack(chat_id, attacker_id, target_id):
    room = GAME_ROOMS[chat_id]

    if attacker_id not in room["players"]:
        return False, "Siz bu o‘yinda emassiz."

    if target_id not in room["players"]:
        return False, "O‘yinchi topilmadi."

    if room["hp"].get(attacker_id, 0) <= 0:
        return False, "Siz jangdan chiqdingiz."

    if room["hp"].get(target_id, 0) <= 0:
        return False, "Bu o‘yinchi allaqachon jangdan chiqqan."

    if room["sides"].get(attacker_id) == room["sides"].get(target_id):
        return False, "O‘z jamoangizga hujum qilib bo‘lmaydi."

    weapon_id = resolve_weapon_id(room.get("weapon", {}).get(attacker_id, "pistol"))
    damage = WEAPONS[weapon_id]["damage"]

    if room["defense_used"].get(target_id):
        room["defense_used"][target_id] = False
        damage = 0

    room["hp"][target_id] = max(
        0,
        room["hp"][target_id] - damage
    )

    attacker_name = (
        room.get("users", {})
        .get(attacker_id, {})
        .get("name")
        or f"O‘yinchi {attacker_id}"
    )

    target_name = (
        room.get("users", {})
        .get(target_id, {})
        .get("name")
        or f"O‘yinchi {target_id}"
    )

    room.setdefault("round_logs", []).append({
        "attacker_id": attacker_id,
        "attacker_name": attacker_name,
        "target_id": target_id,
        "target_name": target_name,
        "damage": damage,
        "target_hp": room["hp"][target_id],
    })

    return True, damage


async def battle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = context.user_data.get("battle_chat_id")

    if chat_id is None:
        await query.answer(
            "❌ Faol jang topilmadi. Guruhdagi 🤖 Jangga kirish tugmasidan kiring.",
            show_alert=True
        )
        return

    if chat_id not in GAME_ROOMS:
        await query.answer(
            "O‘yin topilmadi.",
            show_alert=True
        )
        return

    room = GAME_ROOMS[chat_id]

    if user_id not in room["players"]:
        await query.answer(
            "Siz bu o‘yinda emassiz.",
            show_alert=True
        )
        return

    if room["hp"].get(user_id, 0) <= 0:
        await query.answer(
            "Siz jangdan chiqdingiz.",
            show_alert=True
        )
        return

    data = query.data

    # ASOSIY JANG MENYUSI
    if data == "battle_menu":
        await query.edit_message_text(
            battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

    # HUJUM
    if data == "battle_attack":
        enemies = alive_players(
            room,
            "red" if room["sides"].get(user_id) == "blue" else "blue"
        )

        if not enemies:
            await query.answer(
                "Raqib qolmagan.",
                show_alert=True
            )
            return

        await query.edit_message_text(
            "🎯 Raqibni tanlang:",
            reply_markup=attack_keyboard(
                chat_id,
                user_id
            )
        )
        return

    # RAQIB TANLASH
    if data.startswith("attack_target:"):
        try:
            target_id = int(data.split(":")[1])
        except ValueError:
            await query.answer(
                "Noto‘g‘ri o‘yinchi.",
                show_alert=True
            )
            return

        success, result = attack(
            chat_id,
            user_id,
            target_id
        )

        if not success:
            await query.answer(
                result,
                show_alert=True
            )
            return

        # ⚔️ Hujum ma'lumotlari
        attacker_name = (
            room.get("users", {})
            .get(user_id, {})
            .get("name")
            or f"O'yinchi {user_id}"
        )

        target_name = (
            room.get("users", {})
            .get(target_id, {})
            .get("name")
            or f"O'yinchi {target_id}"
        )

        target_hp = room["hp"].get(target_id, 0)

        # 📢 Hujumni darhol guruhga chiqaramiz.
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⚔️ HUJUM\n\n"
                    f"👤 {attacker_name}\n"
                    f"🎯 {target_name}\n"
                    f"💥 {result} zarar\n"
                    f"❤️ {target_name}: {target_hp} HP"
                )
            )
        except Exception:
            pass

        winner = check_winner(chat_id)

        if winner:
            winner_name = (
                "🔵 KO‘K" if winner == "blue"
                else "🔴 QIZIL"
            )

            room["phase"] = "finished"

            # ⏱️ G‘alabadan keyin timer to‘xtaydi.
            await stop_battle_timer(chat_id)

            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🏆 {winner_name} G‘OLIB!\n\n"
                        f"⚔️ Oxirgi hujum: {attacker_name}\n"
                        f"🎯 Nishon: {target_name}\n"
                        f"💥 Zarar: {result}"
                    )
                )
            except Exception:
                pass

            await query.edit_message_text(
                f"🏆 {winner_name} G‘OLIB!\n\n"
                f"💥 Yetkazilgan zarar: {result}\n"
                f"❤️ {target_name}: 0 HP"
            )
            return

        await query.edit_message_text(
            battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

        winner = check_winner(chat_id)

        if winner:
            winner_name = (
                "🔵 KO‘K" if winner == "blue"
                else "🔴 QIZIL"
            )

            room["phase"] = "finished"

            await query.edit_message_text(
                f"🏆 {winner_name} G‘OLIB!\n\n"
                f"💥 Yetkazilgan zarar: {result}\n"
                "❤️ Raqib HP: 0"
            )
            return

        await query.edit_message_text(
            battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

    # HIMOYA
    if data == "battle_defense":
        if room["defense_used"].get(user_id):
            await query.answer(
                "🛡 Himoyani allaqachon ishlatgansiz.",
                show_alert=True
            )
            return

        room["defense_used"][user_id] = True

        await query.edit_message_text(
            "🛡 Himoya yoqildi!\n\n"
            "Keyingi keladigan zarba bloklanadi.\n\n"
            + battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

    # APTECHKA
    if data == "battle_medkit":
        used = room["medkit_used"].get(user_id, 0)
        hp = room["hp"].get(user_id, 0)

        if used >= 3:
            await query.answer(
                "💊 Aptechka tugagan.",
                show_alert=True
            )
            return

        if hp >= 100:
            await query.answer(
                "❤️ HP allaqachon 100.",
                show_alert=True
            )
            return

        heal = 50
        old_hp = hp

        room["hp"][user_id] = min(
            100,
            hp + heal
        )

        room["medkit_used"][user_id] += 1

        actual_heal = room["hp"][user_id] - old_hp

        await query.edit_message_text(
            f"💊 Aptechka ishlatildi!\n\n"
            f"❤️ +{actual_heal} HP\n"
            f"❤️ HP: {room['hp'][user_id]}/100\n\n"
            + battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

    # QUROL TANLASH
    if data == "battle_weapon":
        await query.edit_message_text(
            "🔫 Qurolni tanlang:",
            reply_markup=weapon_keyboard()
        )
        return

    # QUROLNI O‘ZGARTIRISH
    if data.startswith("weapon:"):
        weapon_id = data.split(":", 1)[1]

        if weapon_id not in WEAPONS:
            await query.answer(
                "Qurol topilmadi.",
                show_alert=True
            )
            return

        if "weapon" not in room:
            room["weapon"] = {}

        room["weapon"][user_id] = weapon_id

        await query.edit_message_text(
            f"🔫 Tanlangan qurol:\n"
            f"{WEAPONS[weapon_id]['name']}\n\n"
            + battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
