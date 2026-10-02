import json
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


DATA_FILE = "data/users.json"

# TOKENNI EMAS, bosh admin IDni keyin shu yerga qo‘yamiz.
# Masalan: MAIN_ADMIN_ID = 123456789
MAIN_ADMIN_ID = 0


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "admins": [],
            "settings": {
                "win_reward": 50,
                "team_bonus": 50,
                "win_streak_for_almas": 10
            }
        }

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    os.makedirs("data", exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


def ensure_user(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "pul": 0,
            "almas": 0,
            "win_streak": 0
        }
        save_data(data)

    return data


def is_admin(user_id):
    data = load_data()

    if user_id == MAIN_ADMIN_ID:
        return True

    return user_id in data.get("admins", [])


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
