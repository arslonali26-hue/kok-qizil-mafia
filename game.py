import asyncio
import time
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


GAME_ROOMS = {}

async def stop_battle_timer(chat_id):
    room = GAME_ROOMS.get(chat_id)
    if not room:
        return

    task = room.get("timer_task")
    if task and not task.done():
        task.cancel()

    room["timer_task"] = None


async def battle_timer_loop(chat_id, application):
    while True:
        try:
            room = GAME_ROOMS.get(chat_id)

            if not room or room.get("phase") != "battle":
                print(f"⏱️ TIMER: jang tugagan yoki xona topilmadi: {chat_id}")
                return

            timer_seconds = int(room.get("battle_timer", 10))

            print(
                f"⏱️ TIMER: chat={chat_id}, "
                f"raund={room.get("round_number", 1)}, "
                f"vaqt={timer_seconds}s"
            )

            await asyncio.sleep(timer_seconds)

            room = GAME_ROOMS.get(chat_id)

            if not room or room.get("phase") != "battle":
                print(f"🛑 TIMER: jang sleepdan keyin tugagan: {chat_id}")
                return

            finished_logs = list(room.get("round_logs", []))
            finished_round = room.get("round_number", 1)

            blue_alive = [
                uid for uid in room.get("players", [])
                if room.get("sides", {}).get(uid) == "blue"
                and room.get("hp", {}).get(uid, 0) > 0
            ]

            red_alive = [
                uid for uid in room.get("players", [])
                if room.get("sides", {}).get(uid) == "red"
                and room.get("hp", {}).get(uid, 0) > 0
            ]

            if not blue_alive or not red_alive:
                print(
                    f"🏆 TIMER: g'olib aniqlandi, "
                    f"timer tugadi: {chat_id}"
                )
                return

            lines = [
                f"🔄 RAUND {finished_round} YAKUNI",
                ""
            ]

            if finished_logs:
                for log in finished_logs:
                    lines.append(
                        f"👤 {log.get('attacker_name', 'Noma\'lum')}"
                    )
                    lines.append(
                        f"🎯 {log.get('target_name', 'Noma\'lum')}"
                    )
                    lines.append(
                        f"💥 {log.get('damage', 0)} zarar"
                    )
                    lines.append(
                        f"❤️ {log.get('target_name', 'Noma\'lum')}: "
                        f"{log.get('target_hp', 0)} HP"
                    )
                    lines.append("")
            else:
                lines.append("📭 Bu raundda hujum bo‘lmadi.")
                lines.append("")

            lines.append(
                f"⏱️ Keyingi raund: {timer_seconds} soniya"
            )

            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text="\n".join(lines)
                )
                print(
                    f"📢 TIMER: RAUND {finished_round} "
                    f"yakuni guruhga yuborildi"
                )
            except Exception as e:
                print(
                    f"❌ TIMER send_message xatosi: {e}"
                )

            from config import ROUND_ENERGY_REGEN

            for user_id in room.get("players", []):
                if room.get("hp", {}).get(user_id, 0) > 0:
                    current_energy = room["energy"].get(user_id, 0)

                    room["energy"][user_id] = min(
                        100,
                        current_energy + ROUND_ENERGY_REGEN
                    )

            room["round_number"] = finished_round + 1
            room["round_logs"] = []
            room["round_started_at"] = time.time()

            print(
                f"🔄 TIMER: yangi raund boshlandi: "
                f"{room['round_number']} | chat={chat_id}"
            )

            # 👥 LIVE HP — har yangi raundda haqiqiy HP holatini chiqarish.
            # Mavjud jang mexanikasi o'zgartirilmaydi.
            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=battle_live_players_text(room),
                    reply_markup=battle_live_players_keyboard(room),
                )

                print(
                    f"✅ LIVE HP ROUND REFRESH: "
                    f"raund={room['round_number']} | "
                    f"chat={chat_id}"
                )

            except Exception as e:
                print(
                    f"❌ LIVE HP ROUND REFRESH XATOSI: "
                    f"raund={room.get('round_number', 0)} | "
                    f"chat={chat_id} | error={e}"
                )

            # PRIVATE_BATTLE_REFRESH_V8
            # 📩 Har yangi raundda yangi private Battle panel.
            # Eski Battle xabarlari o‘chirilmaydi.
            try:
                from bot import battle_text, battle_keyboard

                for player_id in participants(chat_id):
                    try:
                        await application.bot.send_message(
                            chat_id=player_id,
                            text=(
                                f"⚔️ JANG — "
                                f"{room['round_number']}-RAUND\n\n"
                                + battle_text(room, player_id)
                            ),
                            reply_markup=battle_keyboard(),
                        )

                        print(
                            f"✅ PRIVATE BATTLE REFRESH: "
                            f"player={player_id} "
                            f"raund={room['round_number']} "
                            f"chat={chat_id}"
                        )

                    except Exception as e:
                        print(
                            f"❌ PRIVATE BATTLE REFRESH XATOSI: "
                            f"player={player_id} "
                            f"raund={room['round_number']} "
                            f"error={e}"
                        )

            except Exception as e:
                print(
                    f"❌ PRIVATE BATTLE REFRESH IMPORT XATOSI: "
                    f"chat={chat_id} error={e}"
                )

        except asyncio.CancelledError:
            print(
                f"🛑 TIMER: task bekor qilindi: {chat_id}"
            )
            return

        except Exception as e:
            print(
                f"❌ TIMER XATOSI: "
                f"chat={chat_id} | "
                f"{type(e).__name__}: {e}"
            )
            await asyncio.sleep(1)



def battle_live_players_keyboard(room):
    """
    ⚔️ Jangdagi tirik o‘yinchilar.
    🔢 Lobby raqami lobby tugaguncha o‘zgarmaydi.
    👤 Username mavjud bo‘lsa, ism bosilganda Telegram profiliga o'tadi.

    ⚠️ tg://user?id=... ishlatilmaydi.
    Bu Button_user_privacy_restricted xatosini oldini oladi.
    """

    blue = []
    red = []

    player_numbers = room.get("player_numbers", {})

    for user_id in room.get("players", []):
        hp = int(room.get("hp", {}).get(user_id, 0))

        # 💀 O‘lganlar ko‘rsatilmaydi.
        if hp <= 0:
            continue

        user = room.get("users", {}).get(user_id, {})
        name = user.get("name") or f"ID {user_id}"
        username = str(user.get("username") or "").strip().lstrip("@")

        number = player_numbers.get(user_id)

        if number is None:
            number = user_id

        if hp < 100:
            button_text = f"{number}. {name} — ❤️ {hp} HP"
        else:
            button_text = f"{number}. {name}"

        # 👤 Faqat username mavjud bo‘lsa profil linki beriladi.
        if username:
            button = InlineKeyboardButton(
                button_text,
                url=f"https://t.me/{username}"
            )
        else:
            # Username yo‘q foydalanuvchida oddiy tugma.
            # tg://user?id= ishlatilmaydi.
            button = InlineKeyboardButton(
                button_text,
                callback_data="battle_live_noop"
            )

        side = room.get("sides", {}).get(user_id)

        if side == "blue":
            blue.append((number, button))
        elif side == "red":
            red.append((number, button))

    blue.sort(key=lambda x: x[0])
    red.sort(key=lambda x: x[0])

    keyboard = []

    for _, button in blue:
        keyboard.append([button])

    for _, button in red:
        keyboard.append([button])

    # 🤖 Botga o‘tish
    # Faqat bot chatini ochadi, hech qanday /start yoki buyruq yubormaydi.
    bot_username = room.get("bot_username")

    if bot_username:
        keyboard.append([
            InlineKeyboardButton(
                "🤖 BOTGA O‘TISH",
                url=f"https://t.me/{bot_username}"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


def battle_live_players_text(room):
    """
    ⚔️ Jangdagi barcha tirik o‘yinchilar.
    🔢 Raqam lobby davomida o‘zgarmaydi.
    """

    blue = []
    red = []

    player_numbers = room.get("player_numbers", {})

    for user_id in room.get("players", []):
        hp = int(room.get("hp", {}).get(user_id, 0))

        # 💀 O‘lgan o‘yinchilar yashiriladi.
        if hp <= 0:
            continue

        user = room.get("users", {}).get(user_id, {})
        name = user.get("name") or f"ID {user_id}"

        number = player_numbers.get(user_id)

        # 🔢 Raqam bo‘lmasa fallback.
        if number is None:
            number = user_id

        # ❤️ Faqat zararlangan o‘yinchida HP ko‘rsatiladi.
        if hp < 100:
            line = f"{number}. {name} — ❤️ {hp} HP"
        else:
            line = f"{number}. {name}"

        side = room.get("sides", {}).get(user_id)

        if side == "blue":
            blue.append((number, line))
        elif side == "red":
            red.append((number, line))

    # 🔢 Random berilgan raqam bo‘yicha tartib.
    blue.sort(key=lambda x: x[0])
    red.sort(key=lambda x: x[0])

    round_number = int(room.get("round_number", 1))

    lines = [
        f"⚔️ TIRIK O‘YINCHILAR — {round_number}-RAUND",
        "",
        "🔵 KO‘KLAR",
        "",
    ]

    if blue:
        lines.extend(line for _, line in blue)
    else:
        lines.append("💀 Tirik o‘yinchi yo‘q.")

    lines.extend([
        "",
        "🔴 QIZILLAR",
        "",
    ])

    if red:
        lines.extend(line for _, line in red)
    else:
        lines.append("💀 Tirik o‘yinchi yo‘q.")

    return "\n".join(lines)


def start_battle_timer(chat_id, application):
    room = GAME_ROOMS.get(chat_id)

    if not room:
        return

    old_task = room.get("timer_task")

    if old_task and not old_task.done():
        old_task.cancel()

    room["timer_task"] = asyncio.create_task(
        battle_timer_loop(chat_id, application)
    )


def create_room(chat_id):
    GAME_ROOMS[chat_id] = {
        "players": [],
        "player_numbers": {},
        "users": {},
        "sides": {},
        "hp": {},
        "energy": {},
        "defense_used": {},
        "medkit_used": {},
        "phase": "waiting",
        "started_by": None,
        "message_id": None,
        "battle_timer": 10,
        "round_number": 0,
        "round_started_at": None,
        "round_logs": [],
        "private_messages": {},
        "timer_task": None,
    }


def add_player(chat_id, user):
    room = GAME_ROOMS[chat_id]
    user_id = user.id

    if user_id not in room["players"]:
        room["players"].append(user_id)

    room["users"][user_id] = {
        "name": user.full_name or "Noma'lum",
        "username": user.username or "",
    }

    room["hp"].setdefault(user_id, 100)
    room["energy"].setdefault(user_id, 100)
    room["defense_used"].setdefault(user_id, False)
    room["medkit_used"].setdefault(user_id, 0)


def remove_player(chat_id, user_id):
    room = GAME_ROOMS.get(chat_id)

    if not room:
        return False

    if user_id in room["players"]:
        room["players"].remove(user_id)

    room["users"].pop(user_id, None)
    room["sides"].pop(user_id, None)
    room["hp"].pop(user_id, None)
    room["energy"].pop(user_id, None)
    room["defense_used"].pop(user_id, None)
    room["medkit_used"].pop(user_id, None)

    return True


def choose_side(chat_id, user_id, side):
    room = GAME_ROOMS.get(chat_id)

    if not room:
        return False

    if room.get("phase") != "waiting":
        return False

    if user_id not in room["players"]:
        return False

    if side not in ("blue", "red"):
        return False

    room["sides"][user_id] = side
    return True


def get_team_players(chat_id):
    room = GAME_ROOMS[chat_id]

    blue = []
    red = []

    for user_id in room["players"]:
        side = room["sides"].get(user_id)

        if side == "blue":
            blue.append(user_id)
        elif side == "red":
            red.append(user_id)

    return blue, red


def participants(chat_id):
    room = GAME_ROOMS.get(chat_id)

    if not room:
        return []

    # Faqat haqiqatan 🔵 yoki 🔴 tanlaganlar.
    return [
        user_id
        for user_id in room["players"]
        if user_id in room["sides"]
    ]


def team_keyboard(room, show_start=True):
    keyboard = []

    blue = []
    red = []

    for user_id in room["players"]:
        side = room["sides"].get(user_id)
        user = room.get("users", {}).get(user_id, {})
        name = user.get("name", f"ID {user_id}")

        # Telegram ba'zi akkauntlarda tg://user havolasini
        # inline tugmada cheklashi mumkin.
        # Shuning uchun ism hozir xavfsiz callback tugma sifatida ko'rsatiladi.
        button = InlineKeyboardButton(
            f"👤 {name}",
            callback_data=f"game_player_{user_id}"
        )

        if side == "blue":
            blue.append([button])
        elif side == "red":
            red.append([button])

    keyboard.append([
        InlineKeyboardButton(
            f"🔵 KO‘K — {len(blue)} ta",
            callback_data="game_info_blue"
        )
    ])

    keyboard.extend(blue)

    keyboard.append([
        InlineKeyboardButton(
            f"🔴 QIZIL — {len(red)} ta",
            callback_data="game_info_red"
        )
    ])

    keyboard.extend(red)

    keyboard.append([
        InlineKeyboardButton(
            "🔵 KO‘K",
            callback_data="game_side_blue"
        ),
        InlineKeyboardButton(
            "🔴 QIZIL",
            callback_data="game_side_red"
        )
    ])

    if show_start:
        keyboard.append([
            InlineKeyboardButton(
                "▶️ O‘yinni boshlash",
                callback_data="game_start"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


def waiting_text(room):
    blue = []
    red = []

    for user_id in room["players"]:
        user = room["users"].get(user_id, {})
        name = user.get("name", f"ID {user_id}")
        side = room["sides"].get(user_id)

        if side == "blue":
            blue.append(f"👤 {name}")
        elif side == "red":
            red.append(f"👤 {name}")

    blue_text = "\n".join(blue) if blue else "— Hali hech kim yo‘q"
    red_text = "\n".join(red) if red else "— Hali hech kim yo‘q"

    return (
        "🔵🔴 KO‘K–QIZIL\n\n"
        "👥 O‘yinchilar yig‘ilmoqda...\n\n"
        f"🔵 KO‘K — {len(blue)} ta\n"
        f"{blue_text}\n\n"
        f"🔴 QIZIL — {len(red)} ta\n"
        f"{red_text}\n\n"
        "👇 Jamoangizni tanlang:"
    )


async def is_group_admin(update, user_id):
    chat = update.effective_chat

    if not chat or chat.type == "private":
        from database import is_admin
        if is_admin(update.effective_user.id):
            await private_battle_start(update, context)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔫 Rollar haqida ma’lumot", callback_data="start_roles_info")],
            [InlineKeyboardButton("👥 Botni guruhga qo‘shish haqida ma’lumot", callback_data="start_add_info")],
            [InlineKeyboardButton("➕ Botni guruhga qo‘shish", url="https://t.me/" + (await context.bot.get_me()).username + "?startgroup=true")],
            [InlineKeyboardButton("💎 Premium guruhlar", callback_data="start_premium_groups")],
        ])
        await update.message.reply_text(
                        "👋 Assalomu alaykum!\n\nKerakli bo‘limni tanlang:",

            reply_markup=keyboard,
        )
        return

    try:
        member = await chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def can_manage_game(update, context):
    user_id = update.effective_user.id

    # 🤖 Bot administratori
    try:
        from database import is_admin

        if is_admin(user_id):
            return True
    except Exception:
        pass

    # 👑 Guruh administratori
    return await is_group_admin(update, user_id)


async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if not chat or chat.type == "private":
        from database import is_admin
        if is_admin(update.effective_user.id):
            await private_battle_start(update, context)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔫 Rollar haqida ma’lumot", callback_data="start_roles_info")],
            [InlineKeyboardButton("👥 Botni guruhga qo‘shish haqida ma’lumot", callback_data="start_add_info")],
            [InlineKeyboardButton("➕ Botni guruhga qo‘shish", url="https://t.me/" + (await context.bot.get_me()).username + "?startgroup=true")],
            [InlineKeyboardButton("💎 Premium guruhlar", callback_data="start_premium_groups")],
        ])
        await update.message.reply_text(
                        "👋 Assalomu alaykum!\n\nKerakli bo‘limni tanlang:",

            reply_markup=keyboard,
        )
        return

    # 🔐 /game faqat guruh admini yoki bot admini
    if not await can_manage_game(update, context):
        await update.message.reply_text(
            "⛔ Bu buyruqni faqat guruh yoki bot administratori ishlata oladi."
        )
        return

    chat_id = chat.id

    # 🔄 Mavjud Game bo‘lsa — yangi room ochmaymiz.
    if chat_id in GAME_ROOMS:
        room = GAME_ROOMS[chat_id]

        # ⚔️ Jang boshlangan bo‘lsa, mavjud battle holatiga tegmaymiz.
        if room.get("phase") != "waiting":
            await update.message.reply_text(
                "⚔️ Bu Game allaqachon boshlangan.\n\n"
                f"🎮 Holat: {room.get('phase', 'battle')}\n"
                f"👥 Ishtirokchilar: {len(participants(chat_id))} ta"
            )
            return

        old_message_id = room.get("message_id")

        # 📌 Eski Game xabarini unpin qilamiz.
        if old_message_id:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=chat_id,
                    message_id=old_message_id
                )
                print(
                    f"📌 UNPIN OK: chat={chat_id} "
                    f"message={old_message_id}"
                )
            except Exception as e:
                print(
                    f"⚠️ UNPIN O‘TKAZILDI: chat={chat_id} "
                    f"message={old_message_id} error={e}"
                )

            # 🗑️ Eski Game xabarini o‘chiramiz.
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=old_message_id
                )
                print(
                    f"🗑️ OLD GAME MESSAGE DELETED: chat={chat_id} "
                    f"message={old_message_id}"
                )
            except Exception as e:
                print(
                    f"⚠️ OLD GAME DELETE O‘TKAZILDI: "
                    f"chat={chat_id} message={old_message_id} error={e}"
                )

        # 📩 Aynan shu room holatini pastga yangi xabar qilib chiqaramiz.
        sent_message = await update.message.reply_text(
            waiting_text(room),
            reply_markup=team_keyboard(room)
        )

        room["message_id"] = sent_message.message_id

        # 📌 Yangi Game xabarini pin qilamiz.
        try:
            await context.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=sent_message.message_id,
                disable_notification=True
            )
            print(
                f"📌 NEW GAME PIN OK: chat={chat_id} "
                f"message={sent_message.message_id}"
            )
        except Exception as e:
            print(
                f"⚠️ NEW GAME PIN O‘TKAZILDI: "
                f"chat={chat_id} message={sent_message.message_id} error={e}"
            )

        return

    # 🆕 Faqat birinchi /game uchun yangi room.
    create_room(chat_id)
    room = GAME_ROOMS[chat_id]

    sent_message = await update.message.reply_text(
        waiting_text(room),
        reply_markup=team_keyboard(room)
    )

    room["message_id"] = sent_message.message_id

    # 📌 Birinchi Game xabarini pin qilamiz.
    try:
        await context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=sent_message.message_id,
            disable_notification=True
        )
        print(
            f"📌 FIRST GAME PIN OK: chat={chat_id} "
            f"message={sent_message.message_id}"
        )
    except Exception as e:
        print(
            f"⚠️ FIRST GAME PIN O‘TKAZILDI: "
            f"chat={chat_id} message={sent_message.message_id} error={e}"
        )


async def handle_side_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    chat = query.message.chat

    if chat.type == "private":
        await query.answer(
            "👥 Bu o‘yin faqat guruhda ishlaydi.",
            show_alert=True
        )
        return

    chat_id = chat.id

    if chat_id not in GAME_ROOMS:
        await query.answer(
            "❌ Bu guruhda faol o‘yin yo‘q.",
            show_alert=True
        )
        return

    room = GAME_ROOMS[chat_id]

    # 📌 Guruhdagi asosiy Game xabarini eslab qolamiz
    room["message_id"] = query.message.message_id

    if room.get("phase") != "waiting":
        await query.answer(
            "⚔️ O‘yin allaqachon boshlangan.",
            show_alert=True
        )
        return

    user = query.from_user
    user_id = user.id

    # 👤 Faqat jamoa tugmasini bosganda Game'ga qo‘shiladi.
    if user_id not in room["players"]:
        add_player(chat_id, user)

    if query.data == "game_side_blue":
        side = "blue"
        side_name = "🔵 KO‘K"
    elif query.data == "game_side_red":
        side = "red"
        side_name = "🔴 QIZIL"
    else:
        return

    # 🔄 Eski tomoni avtomatik almashtiriladi.
    old_side = room["sides"].get(user_id)
    room["sides"][user_id] = side

    if old_side == side:
        await query.answer(
            f"ℹ️ Siz allaqachon {side_name}dasiz.",
            show_alert=False
        )
    else:
        await query.answer(
            f"✅ Siz {side_name} jamoasiga qo‘shildingiz!"
        )

    await query.edit_message_text(
        waiting_text(room),
        reply_markup=team_keyboard(room)
    )


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat = query.message.chat

    if chat.type == "private":
        await query.answer(
            "👥 O‘yinni guruhdan boshlang.",
            show_alert=True
        )
        return

    chat_id = chat.id

    if chat_id not in GAME_ROOMS:
        await query.answer(
            "❌ Faol o‘yin topilmadi.",
            show_alert=True
        )
        return

    # 🔐 Startni faqat admin bosadi.
    if not await can_manage_game(update, context):
        await query.answer(
            "⛔ O‘yinni faqat guruh yoki bot administratori boshlay oladi.",
            show_alert=True
        )
        return

    room = GAME_ROOMS[chat_id]

    # 📌 O‘yin boshlanganda Game xabarini unpin qilamiz.
    game_message_id = room.get("message_id")
    if game_message_id:
        try:
            await context.bot.unpin_chat_message(
                chat_id=chat_id,
                message_id=game_message_id
            )
            print(
                f"📌 GAME UNPIN — jang boshlandi: "
                f"chat={chat_id} message={game_message_id}"
            )
        except Exception as e:
            print(
                f"⚠️ GAME UNPIN O‘TKAZILDI: "
                f"chat={chat_id} message={game_message_id} error={e}"
            )

    blue, red = get_team_players(chat_id)

    player_count = len(blue) + len(red)

    if player_count < 1:
        await query.answer(
            "❌ Avval kamida 1 ta o‘yinchi jamoaga qo‘shilsin.",
            show_alert=True
        )
        return

    # ⚠️ Jangda raqib bo‘lishi uchun ikkala tomon ham kerak.
    if not blue or not red:
        await query.answer(
            "⚠️ 🔵 Ko‘k va 🔴 Qizil tomonda ham o‘yinchi bo‘lishi kerak.",
            show_alert=True
        )
        return

    room["phase"] = "battle"
    room["started_by"] = query.from_user.id
    room["round_number"] = 1
    room["round_logs"] = []
    room["round_started_at"] = time.time()

    # 🎲 LOBBY RAQAMLARI
    # Har bir jang/lobby uchun bir marta random taqsimlanadi.
    # Raundlar davomida o‘zgarmaydi.
    battle_players = list(participants(chat_id))

    # 🔟 10.3 — Jang boshlanishini TOP tarixiga qayd qilish.
    try:
        from database import load_data, save_data
        from top_stats import top10_1_register_battle

        _top_data = load_data()
        top10_1_register_battle(
            _top_data,
            chat_id,
            battle_players,
            title=getattr(chat, "title", None),
        )

        # 👤 Har bir qatnashchining shaxsiy jang statistikasini yozamiz.
        from top_stats import top10_3_record_group_event

        for _player_id in battle_players:
            top10_3_record_group_event(
                _top_data,
                chat_id,
                _player_id,
                "battles",
                1,
                title=getattr(chat, "title", None),
            )

        save_data(_top_data)

        print(
            f"✅ 10.3 BATTLE START STAT: "
            f"chat={chat_id} players={len(battle_players)}"
        )
    except Exception as e:
        print(
            f"❌ 10.3 BATTLE START STAT XATOSI: "
            f"chat={chat_id} error={e}"
        )
    random_numbers = list(range(1, len(battle_players) + 1))
    random.shuffle(random_numbers)

    room["player_numbers"] = {
        player_id: number
        for player_id, number in zip(
            battle_players,
            random_numbers
        )
    }

    print(
        f"🎲 LOBBY RAQAMLARI: "
        f"{room['player_numbers']} | chat={chat_id}"
    )

    # ⚔️ Faqat haqiqiy qatnashchilarni tayyorlaymiz.
    for player_id in participants(chat_id):
        room["hp"][player_id] = 100
        room["energy"][player_id] = 100
        room["defense_used"][player_id] = False
        room["medkit_used"][player_id] = 0

    # 📩 Jang boshlandi — barcha haqiqiy qatnashchilarga private panel.
    try:
        from bot import battle_text, battle_keyboard

        for player_id in participants(chat_id):
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=battle_text(GAME_ROOMS[chat_id], player_id),
                    reply_markup=battle_keyboard(),
                )
                print(
                    f"✅ PRIVATE BATTLE PANEL YUBORILDI: "
                    f"player={player_id} chat={chat_id}"
                )
            except Exception as e:
                print(
                    f"❌ PRIVATE BATTLE PANEL YUBORILMADI: "
                    f"player={player_id} error={e}"
                )
    except Exception as e:
        print(f"❌ PRIVATE BATTLE PANEL IMPORT XATOSI: {e}")

    me = await context.bot.get_me()
    bot_username = me.username

    # ⏱️ Umumiy battle timer ishga tushadi.
    start_battle_timer(chat_id, context.application)

    room["bot_username"] = bot_username
    bot_url = f"https://t.me/{bot_username}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🤖 Botga o‘tish",
                url=bot_url
            )
        ]
    ])

    text = (
        "⚔️ JANG BOSHLANDI!\n\n"
        "🍀 Barchaga omad!\n\n"
        "👇 Jangni botda davom ettiring."
    )

    await query.answer("⚔️ Jang boshlandi!")

    # 🧹 Yig‘ilish oynasi yopiladi.
    await query.edit_message_text(
        text,
        reply_markup=keyboard
    )


async def private_battle_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "👋 Salom!\n\n"
            "⚔️ Jang oynasiga kirish uchun "
            "guruhdagi 🤖 Botga o‘tish tugmasini bosing."
        )
        return

    parameter = context.args[0]

    if not parameter.startswith("battle_"):
        await update.message.reply_text(
            "❌ Noto‘g‘ri o‘yin havolasi."
        )
        return

    try:
        room_chat_id = int(parameter.split("_", 1)[1])
    except ValueError:
        await update.message.reply_text(
            "❌ O‘yin ma’lumoti noto‘g‘ri."
        )
        return

    if room_chat_id not in GAME_ROOMS:
        await update.message.reply_text(
            "❌ Bu o‘yin tugagan yoki mavjud emas."
        )
        return

    room = GAME_ROOMS[room_chat_id]

    # ❗ Faqat haqiqatan jamoaga qo‘shilganlar.
    if user.id not in room["sides"]:
        await update.message.reply_text(
            "❌ Siz bu Game o‘yiniga qo‘shilmagansiz."
        )
        return

    if room.get("phase") != "battle":
        await update.message.reply_text(
            "⏳ Jang hali boshlanmagan yoki tugagan."
        )
        return

    context.user_data["battle_chat_id"] = room_chat_id

    # bot.py dagi mavjud battle funksiyalaridan foydalanamiz.
    try:
        from bot import battle_text, battle_keyboard

        await update.message.reply_text(
            battle_text(room, user.id),
            reply_markup=battle_keyboard()
        )
    except ImportError:
        await update.message.reply_text(
            "⚔️ Jang boshlandi.\n\n"
            "🎯 Jang oynasi tayyorlanmoqda."
        )



async def group_start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    # /start private chatda bo‘lsa — mavjud private battle tizimi ishlaydi.
    if not chat or chat.type == "private":
        from database import is_admin
        if is_admin(update.effective_user.id):
            await private_battle_start(update, context)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔫 Rollar haqida ma’lumot", callback_data="start_roles_info")],
            [InlineKeyboardButton("👥 Botni guruhga qo‘shish haqida ma’lumot", callback_data="start_add_info")],
            [InlineKeyboardButton("➕ Botni guruhga qo‘shish", url="https://t.me/" + (await context.bot.get_me()).username + "?startgroup=true")],
            [InlineKeyboardButton("💎 Premium guruhlar", callback_data="start_premium_groups")],
        ])
        await update.message.reply_text(
                        "👋 Assalomu alaykum!\n\nKerakli bo‘limni tanlang:",

            reply_markup=keyboard,
        )
        return

    chat_id = chat.id

    if chat_id not in GAME_ROOMS:
        await update.message.reply_text(
            "❌ Bu guruhda faol Game yo‘q."
        )
        return

    # 🔐 Faqat guruh admini yoki bot admini
    if not await can_manage_game(update, context):
        await update.message.reply_text(
            "⛔ O‘yinni faqat guruh yoki bot administratori boshlay oladi."
        )
        return

    room = GAME_ROOMS[chat_id]

    if room.get("phase") != "waiting":
        await update.message.reply_text(
            "⚠️ Bu Game allaqachon boshlangan."
        )
        return

    blue, red = get_team_players(chat_id)
    player_count = len(blue) + len(red)

    if player_count < 1:
        await update.message.reply_text(
            "❌ Avval kamida 1 ta o‘yinchi Game'ga qo‘shilsin."
        )
        return

    room["phase"] = "battle"
    room["started_by"] = update.effective_user.id

    for player_id in participants(chat_id):
        room["hp"][player_id] = 100
        room["energy"][player_id] = 100
        room["defense_used"][player_id] = False
        room["medkit_used"][player_id] = 0

    # 📩 Jang boshlandi — barcha haqiqiy qatnashchilarga private panel.
    try:
        from bot import battle_text, battle_keyboard

        for player_id in participants(chat_id):
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=battle_text(GAME_ROOMS[chat_id], player_id),
                    reply_markup=battle_keyboard(),
                )
                print(
                    f"✅ PRIVATE BATTLE PANEL YUBORILDI: "
                    f"player={player_id} chat={chat_id}"
                )
            except Exception as e:
                print(
                    f"❌ PRIVATE BATTLE PANEL YUBORILMADI: "
                    f"player={player_id} error={e}"
                )
    except Exception as e:
        print(f"❌ PRIVATE BATTLE PANEL IMPORT XATOSI: {e}")

    me = await context.bot.get_me()
    room["bot_username"] = me.username
    bot_url = f"https://t.me/{me.username}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🤖 Botga o‘tish",
                url=bot_url
            )
        ]
    ])

    await update.message.reply_text(
        "⚔️ JANG BOSHLANDI!\n\n"
        "🍀 Barchaga omad!\n\n"
        "👇 Jangni botda davom ettiring.",
        reply_markup=keyboard
    )


async def exit_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    if not chat:
        return

    # Private chatdan /exit yuborilsa,
    # faol Game roomini user orqali topamiz.
    user_id = update.effective_user.id

    found_chat_id = None

    for chat_id, room in GAME_ROOMS.items():
        if user_id in room.get("players", []):
            found_chat_id = chat_id
            break

    if found_chat_id is None:
        await update.message.reply_text(
            "❌ Siz hozir hech qaysi Game'da emassiz."
        )
        return

    room = GAME_ROOMS[found_chat_id]

    remove_player(found_chat_id, user_id)

    # Jangda qolgan odamlar orasida raqib qolmagan bo‘lsa,
    # keyinchalik winner tizimi shu yerga ulanadi.
    if not room["players"]:
        GAME_ROOMS.pop(found_chat_id, None)

    await update.message.reply_text(
        "🚪 Siz o‘yindan chiqdingiz."
    )


async def stop_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    if not chat or chat.type == "private":
        from database import is_admin
        if is_admin(update.effective_user.id):
            await private_battle_start(update, context)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔫 Rollar haqida ma’lumot", callback_data="start_roles_info")],
            [InlineKeyboardButton("👥 Botni guruhga qo‘shish haqida ma’lumot", callback_data="start_add_info")],
            [InlineKeyboardButton("➕ Botni guruhga qo‘shish", url="https://t.me/" + (await context.bot.get_me()).username + "?startgroup=true")],
            [InlineKeyboardButton("💎 Premium guruhlar", callback_data="start_premium_groups")],
        ])
        await update.message.reply_text(
                        "👋 Assalomu alaykum!\n\nKerakli bo‘limni tanlang:",

            reply_markup=keyboard,
        )
        return

    # 🔐 Faqat guruh admini yoki bot admini
    if not await can_manage_game(update, context):
        await update.message.reply_text(
            "⛔ /stop ni faqat guruh yoki bot administratori ishlata oladi."
        )
        return

    chat_id = chat.id

    if chat_id not in GAME_ROOMS:
        await update.message.reply_text(
            "❌ Bu guruhda faol Game yo‘q."
        )
        return

    # 🛑 Har qanday bosqichda butun room o‘chiriladi.
    GAME_ROOMS.pop(chat_id, None)

    await update.message.reply_text(
        "🛑 O‘YIN TO‘XTATILDI\n\n"
        "👑 O‘yin administrator tomonidan to‘xtatildi."
    )

async def setting_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or chat.type == "private":
        from database import is_admin
        if is_admin(update.effective_user.id):
            await private_battle_start(update, context)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔫 Rollar haqida ma’lumot", callback_data="start_roles_info")],
            [InlineKeyboardButton("👥 Botni guruhga qo‘shish haqida ma’lumot", callback_data="start_add_info")],
            [InlineKeyboardButton("➕ Botni guruhga qo‘shish", url="https://t.me/" + (await context.bot.get_me()).username + "?startgroup=true")],
            [InlineKeyboardButton("💎 Premium guruhlar", callback_data="start_premium_groups")],
        ])
        await update.message.reply_text(
                        "👋 Assalomu alaykum!\n\nKerakli bo‘limni tanlang:",

            reply_markup=keyboard,
        )
        return

    if not await can_manage_game(update, context):
        await update.message.reply_text(
            "⛔ ⚙️ Sozlamani faqat guruh yoki bot administratori o‘zgartira oladi."
        )
        return

    group_id = chat.id
    user_id = user.id

    # 💾 Guruh uchun saqlangan timer
    try:
        from database import load_data

        data = load_data()
        group_settings = data.get("group_settings", {})
        saved = group_settings.get(str(group_id), {})
        current = int(saved.get("battle_timer", 10))
    except Exception as e:
        print(f"⚠️ SETTING TIMER O‘QISH XATOSI: {e}")
        current = 10

    buttons = [
        [
            InlineKeyboardButton(
                "⏱️ 10 soniya",
                callback_data=f"setting_timer:{group_id}:10"
            ),
            InlineKeyboardButton(
                "⏱️ 20 soniya",
                callback_data=f"setting_timer:{group_id}:20"
            ),
        ],
        [
            InlineKeyboardButton(
                "⏱️ 30 soniya",
                callback_data=f"setting_timer:{group_id}:30"
            ),
            InlineKeyboardButton(
                "⏱️ 40 soniya",
                callback_data=f"setting_timer:{group_id}:40"
            ),
        ],
        [
            InlineKeyboardButton(
                "⏱️ 50 soniya",
                callback_data=f"setting_timer:{group_id}:50"
            ),
            InlineKeyboardButton(
                "⏱️ 60 soniya",
                callback_data=f"setting_timer:{group_id}:60"
            ),
        ],
    ]

    text = (
        "⚙️ JANG SOZLAMALARI\n\n"
        f"👥 Guruh ID: {group_id}\n"
        f"⏱️ Hozirgi raund vaqti: {current} soniya\n\n"
        "👇 Raund vaqtini tanlang:"
    )

    try:
        # 🔒 Panel faqat /setting bosgan adminning private chatiga yuboriladi
        sent_message = await context.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        # 🔎 Telegram haqiqatan qaysi private chatga yuborganini tekshirish
        print(
            f"✅ PRIVATE SETTING YUBORILDI: "
            f"user={user_id} | group={group_id} | timer={current}s | "
            f"sent_chat={sent_message.chat.id} | "
            f"message_id={sent_message.message_id}"
        )

    except Exception as e:
        print(
            f"❌ PRIVATE SETTING YUBORILMADI: "
            f"user={user_id} | group={group_id} | error={e}"
        )

        await update.message.reply_text(
            "🤖 Avval botga private chatda /start yuboring, "
            "keyin /setting ni qayta bosing."
        )


async def can_manage_setting_group(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    group_id: int
):
    # 🤖 Bot administratori
    try:
        from database import is_admin

        if is_admin(user_id):
            return True
    except Exception:
        pass

    # 👑 Aynan berilgan guruhdagi administratorni tekshirish
    try:
        member = await context.bot.get_chat_member(
            chat_id=group_id,
            user_id=user_id
        )

        return member.status in ("administrator", "creator")

    except Exception as e:
        print(
            f"❌ SETTING ADMIN TEKSHIRUVI XATOSI: "
            f"group={group_id} | user={user_id} | error={e}"
        )
        return False


async def setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    if not data.startswith("setting_timer:"):
        return

    # 🔐 Format:
    # setting_timer:{group_id}:{timer}
    parts = data.split(":")

    if len(parts) != 3:
        await query.answer(
            "❌ Noto‘g‘ri setting ma’lumoti.",
            show_alert=True
        )
        return

    try:
        group_id = int(parts[1])
        timer_seconds = int(parts[2])
    except (ValueError, IndexError):
        await query.answer(
            "❌ Noto‘g‘ri timer qiymati.",
            show_alert=True
        )
        return

    if timer_seconds not in (10, 20, 30, 40, 50, 60):
        await query.answer(
            "❌ Timer faqat 10 / 20 / 30 / 40 / 50 / 60 soniya bo‘lishi mumkin.",
            show_alert=True
        )
        return

    user = update.effective_user

    if not user:
        await query.answer(
            "❌ Foydalanuvchi aniqlanmadi.",
            show_alert=True
        )
        return

    # 🔒 Private callbackni aynan shu guruh uchun qayta tekshiramiz
    if not await can_manage_setting_group(
        context,
        user.id,
        group_id
    ):
        await query.answer(
            "⛔ Siz bu guruh sozlamasini o‘zgartira olmaysiz.",
            show_alert=True
        )
        return

    # 💾 Guruh timerini doimiy saqlash
    try:
        from database import load_data, save_data

        db_data = load_data()
        group_settings = db_data.setdefault("group_settings", {})

        group_settings[str(group_id)] = {
            "battle_timer": timer_seconds
        }

        save_data(db_data)

        print(
            f"✅ GROUP TIMER SAQLANDI: "
            f"group={group_id} | timer={timer_seconds}s"
        )

    except Exception as e:
        print(
            f"❌ GROUP TIMER SAVE XATOSI: "
            f"group={group_id} | timer={timer_seconds}s | error={e}"
        )

        await query.answer(
            "❌ Timer saqlanmadi.",
            show_alert=True
        )
        return

    # ⚔️ Agar hozir faol room bo‘lsa, uning timerini ham darhol yangilaymiz
    room = GAME_ROOMS.get(group_id)

    if room:
        room["battle_timer"] = timer_seconds
        print(
            f"⚔️ ACTIVE ROOM TIMER YANGILANDI: "
            f"group={group_id} | timer={timer_seconds}s"
        )

    await query.answer(
        f"✅ Timer {timer_seconds} soniyaga o‘rnatildi."
    )

    await query.edit_message_text(
        "⚙️ JANG SOZLAMALARI\n\n"
        f"⏱️ Raund vaqti: {timer_seconds} soniya\n\n"
        "✅ Sozlama saqlandi.\n"
        "👥 Bu sozlama faqat shu guruh uchun."
    )
