from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .game import GAME_ROOMS
from .weapons import WEAPONS


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
        buttons.append([
            InlineKeyboardButton(
                f"🎯 O‘yinchi {user_id}",
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

    weapon_id = room.get("weapon", {}).get(user_id, "pistol")
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

    weapon_id = room.get("weapon", {}).get(attacker_id, "pistol")
    damage = WEAPONS[weapon_id]["damage"]

    if room["defense_used"].get(target_id):
        room["defense_used"][target_id] = False
        damage = 0

    room["hp"][target_id] = max(
        0,
        room["hp"][target_id] - damage
    )

    return True, damage


async def battle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id

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
