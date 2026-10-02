
async def topup_start_callback(update, context):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    _, currency = data.split(":", 1)

    if currency not in ("almas", "pul"):
        await query.answer("❌ Valyuta xatosi.", show_alert=True)
        return

    context.user_data["topup_currency"] = currency
    context.user_data["topup_waiting_amount"] = True

    if currency == "almas":
        text = "🔷 ALMAS QO‘SHISH\n\n🔢 Qancha Almas kerak?\n\n✍️ Miqdorni raqam bilan yozing."
    else:
        text = "🪙 PUL QO‘SHISH\n\n🔢 Qancha Pul kerak?\n\n✍️ Miqdorni raqam bilan yozing."

    await query.message.reply_text(text)


async def topup_amount_handler(update, context):
    # 💎 Premium guruh ID kiritish holati
    if context.user_data.get("admin_premium_state") == "add_group":
        await admin_premium_add_group_text(update, context)
        return

    if not context.user_data.get("topup_waiting_amount"):
        return

    message = update.message
    if not message or not message.text:
        return

    raw = message.text.strip().replace(" ", "").replace(",", "")

    if not raw.isdigit():
        await message.reply_text("❌ Faqat raqam kiriting.")
        return

    amount = int(raw)

    if amount <= 0 or amount > 1_000_000_000:
        await message.reply_text("❌ Miqdor 1 dan 1 000 000 000 gacha bo‘lishi kerak.")
        return

    currency = context.user_data.get("topup_currency")

    if currency == "almas":
        currency_text = "🔷 Almas"
        amount_text = f"{amount:,} Almas"
    elif currency == "pul":
        currency_text = "🪙 Pul"
        amount_text = f"{amount:,} Pul"
    else:
        context.user_data.pop("topup_currency", None)
        context.user_data.pop("topup_waiting_amount", None)
        await message.reply_text("❌ To‘lov turi topilmadi.")
        return

    context.user_data["topup_waiting_amount"] = False

    admin_id = 7979870096
    user = message.from_user
    name = user.full_name or "Noma’lum"
    username = f"@{user.username}" if user.username else "Username yo‘q"

    admin_text = (
        "💳 <b>YANGI TO‘LOV SO‘ROVI</b>\n\n"
        f"👤 Foydalanuvchi: <a href=\"tg://user?id={user.id}\">{name}</a>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📱 Username: {username}\n\n"
        f"💰 Kerakli valyuta: <b>{currency_text}</b>\n"
        f"🔢 Miqdor: <b>{amount_text}</b>\n\n"
        "⏳ To‘lov kutilmoqda."
    )

    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Qabul qilish",
                callback_data=f"topup_accept:{currency}:{user.id}:{amount}",
            ),
            InlineKeyboardButton(
                "❌ Rad etish",
                callback_data=f"topup_reject:{currency}:{user.id}:{amount}",
            ),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            parse_mode="HTML",
            reply_markup=admin_keyboard,
        )
    except Exception:
        pass

    payment_url = f"tg://user?id={admin_id}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💳 To‘lov qilish",
                url=payment_url,
            )
        ]
    ])

    await message.reply_text(
        "💳 <b>TO‘LOV QILISH</b>\n\n"
        f"👤 Siz: <b>{name}</b>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"💰 Valyuta: <b>{currency_text}</b>\n"
        f"🔢 Miqdor: <b>{amount_text}</b>\n\n"
        "👇 To‘lov qilish uchun admin bilan bog‘laning.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def topup_admin_callback(update, context):
    query = update.callback_query

    # 👑 Faqat asosiy admin
    if query.from_user.id != 7979870096:
        await query.answer("❌ Siz admin emassiz.", show_alert=True)
        return

    data = query.data or ""
    parts = data.split(":")

    if len(parts) != 4:
        await query.answer("❌ So‘rov ma’lumoti xato.", show_alert=True)
        return

    action, currency, user_id_text, amount_text = parts

    try:
        user_id = int(user_id_text)
        amount = int(amount_text)
    except ValueError:
        await query.answer("❌ So‘rov ma’lumoti xato.", show_alert=True)
        return

    if action not in ("topup_accept", "topup_reject"):
        await query.answer("❌ Noma’lum amal.", show_alert=True)
        return

    if currency not in ("almas", "pul") or amount <= 0:
        await query.answer("❌ To‘lov ma’lumoti xato.", show_alert=True)
        return

    # 🔒 Bir xil so‘rovni qayta ishlatmaslik
    request_key = f"topup_done:{currency}:{user_id}:{amount}"

    done_requests = context.application.bot_data.setdefault(
        "topup_done_requests", set()
    )

    if request_key in done_requests:
        await query.answer(
            "⚠️ Bu to‘lov so‘rovi allaqachon qayta ishlangan.",
            show_alert=True,
        )
        return

    if action == "topup_reject":
        done_requests.add(request_key)

        await query.edit_message_text(
            query.message.text_html
            + "\n\n❌ <b>RAD ETILDI</b>",
            parse_mode="HTML",
        )

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ <b>TO‘LOV SO‘ROVI RAD ETILDI</b>\n\n"
                    f"🔢 Miqdor: <b>{amount:,}</b>\n"
                    f"💰 Valyuta: <b>{'🔷 Almas' if currency == 'almas' else '🪙 Pul'}</b>\n\n"
                    "ℹ️ Admin tomonidan to‘lov tasdiqlanmadi."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

        await query.answer("❌ To‘lov rad etildi.")
        return

    # 💾 Foydalanuvchi balansini oshirish
    from database import ensure_user, get_user, load_data, save_data

    ensure_user(user_id)
    user = get_user(user_id)

    if not user:
        await query.answer(
            "❌ Foydalanuvchi topilmadi.",
            show_alert=True,
        )
        return

    if currency == "almas":
        user["almas"] = int(user.get("almas", 0)) + amount
        currency_text = "🔷 Almas"
    else:
        user["pul"] = int(user.get("pul", 0)) + amount
        currency_text = "🪙 Pul"

    data_all = load_data()
    data_all["users"][str(user_id)] = user
    save_data(data_all)

    done_requests.add(request_key)

    # 👑 Admin xabarini yopish
    try:
        await query.edit_message_text(
            query.message.text_html
            + f"\n\n✅ <b>QABUL QILINDI</b>\n"
              f"💰 Berildi: <b>{amount:,} {currency_text}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    # 👤 Foydalanuvchiga xabar
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>TO‘LOV QABUL QILINDI!</b>\n\n"
                f"💰 Hisobingizga <b>{amount:,} {currency_text}</b> qo‘shildi.\n\n"
                "✅ Balansingiz yangilandi."
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass

    await query.answer("✅ To‘lov qabul qilindi!")


import asyncio
import html
import random
import uuid
from datetime import datetime, timedelta

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, MAIN_ADMIN_ID
from database import (
    load_data,
    save_data,
    ensure_user,
    get_user,
    is_admin,
)
from moderation import (
    settinghelp_command,
    moderation_callback,
    antilink_message,
    antireklama_message,
    antirepeat_message,
    anticaps_message,
    antimention_message,
    antiflood_message,
    warn_command,
    warns_command,
    delwarn_command,
    resetwarns_command,
    mute_command,
    unmute_command,
    ban_command,
    unban_command,
    kick_command,
    adminn_command,
    unadminn_command,
    adminn_callback,

    del_command,

    purge_command,

    pin_command,

    unpin_command,
)
from game import (
    GAME_ROOMS,
    game_command,
    handle_side_selection,
    start_game,
    private_battle_start,
    group_start_command,
    exit_game,
    stop_game,
    stop_battle_timer,
    setting_command,
    setting_callback,
    is_group_admin,
)
from weapons import (
    WEAPONS,
    get_weapon,
    resolve_weapon_id,
    add_weapon_xp,
    xp_capacity,
    weapon_damage,
)
from achievements import (
    check_achievements,
    achievements_text,
)
from ranking import ranking_text
from top_stats import (
    top10_1_group_summary,
    player_top,
    format_player_top,
    group_player_top,
    format_group_player_top,
)
from profile import profile_command, profile_callback
from inventory import inventory_command, inventory_callback
from shop import (
    shop_command,
    shop_callback,
    shop_add_command,
    shop_delete_command,
    shop_price_command,
    admin_shop_callback,
    admin_shop_text_handler,
    load_shop,
)



# ==========================================================
# 💎 PREMIUM GURUH ID KIRITISH
# ==========================================================

async def admin_premium_add_group_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    user = update.effective_user
    if not is_admin(user.id):
        return

    if context.user_data.get("admin_premium_state") != "add_group":
        return

    raw_id = update.message.text.strip()

    try:
        group_id = int(raw_id)
    except ValueError:
        await update.message.reply_text(
            "❌ Guruh ID faqat raqam bo‘lishi kerak.\n\n"
            "Masalan:\n"
            "-1003555098763"
        )
        return

    data_store = load_data()
    groups = data_store.setdefault("groups", {})
    key = str(group_id)

    if key not in groups:
        groups[key] = {
            "title": "Noma'lum guruh",
            "premium_plan": None,
            "premium_until": None,
            "premium_active": False,
        }

    group = groups[key]

    # Yangi guruh yozuvida ham kerakli maydonlar bo‘lsin
    group.setdefault("title", "Noma'lum guruh")
    group.setdefault("premium_plan", None)
    group.setdefault("premium_until", None)
    group.setdefault("premium_active", False)

    save_data(data_store)

    context.user_data.pop("admin_premium_state", None)

    await update.message.reply_text(
        "👥 GURUH TANLANDI\n\n"
        f"🏷️ Nomi: {group.get('title') or 'Noma\'lum guruh'}\n"
        f"🆔 ID: {group_id}\n\n"
        "💎 Endi Premium muddatini tanlang:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{plan.get('name', plan_key)} — 💎 {int(plan.get('price', 0))}",
                    callback_data=f"admin_premium:grantplan:{group_id}:{plan_key}",
                )
            ]
            for plan_key, plan in data_store.get("settings", {}).get(
                "premium_plans", {}
            ).items()
        ] + [
            [
                InlineKeyboardButton(
                    "🔙 Premium",
                    callback_data="admin_premium",
                )
            ]
        ]),
    )


# ==========================================================
# 🎁 GIVEAWAY SYSTEM V1
# ==========================================================

GIVEAWAY_LOCKS = {}


def _giveaway_lock(giveaway_id):
    lock = GIVEAWAY_LOCKS.get(giveaway_id)
    if lock is None:
        lock = asyncio.Lock()
        GIVEAWAY_LOCKS[giveaway_id] = lock
    return lock


def _giveaway_name(user):
    if not user:
        return "O‘yinchi"
    return user.first_name or user.username or "O‘yinchi"


def _giveaway_mention(user_id, name):
    return (
        f'<a href="tg://user?id={int(user_id)}">'
        f'{html.escape(name or "O‘yinchi")}</a>'
    )


def _giveaway_amount_text(amount, currency):
    if currency == "pul":
        return f"🪙 {amount:,} Pul"
    return f"🔷 {amount:,} Almas"


def _giveaway_currency_short(currency):
    return "Pul" if currency == "pul" else "Almas"


def _giveaway_keyboard(giveaway_id, full=False):
    label = "🔒 JOYLAR TO‘LDI" if full else "🎟️ QATNASHISH"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                label,
                callback_data=f"giveaway_join:{giveaway_id}",
            )
        ]
    ])


def _giveaway_stop_keyboard(giveaway_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛑 To‘xtatish",
                callback_data=f"giveaway_stop:{giveaway_id}",
            )
        ]
    ])


def _giveaway_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data="giveaway_confirm",
            ),
            InlineKeyboardButton(
                "❌ Bekor qilish",
                callback_data="giveaway_cancel",
            ),
        ]
    ])


def _giveaway_limit_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1", callback_data="giveaway_limit:1"),
            InlineKeyboardButton("5", callback_data="giveaway_limit:5"),
            InlineKeyboardButton("10", callback_data="giveaway_limit:10"),
        ],
        [
            InlineKeyboardButton("20", callback_data="giveaway_limit:20"),
            InlineKeyboardButton("34", callback_data="giveaway_limit:34"),
            InlineKeyboardButton("50", callback_data="giveaway_limit:50"),
        ],
        [
            InlineKeyboardButton("75", callback_data="giveaway_limit:75"),
            InlineKeyboardButton("100", callback_data="giveaway_limit:100"),
        ],
        [
            InlineKeyboardButton(
                "✍️ Boshqa son",
                callback_data="giveaway_limit_custom",
            )
        ],
    ])


def _giveaway_currency_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🪙 Pul",
                callback_data="giveaway_currency:pul",
            ),
            InlineKeyboardButton(
                "🔷 Almas",
                callback_data="giveaway_currency:almas",
            ),
        ]
    ])


def _giveaway_text(giveaway):
    participants = giveaway.get("participants", [])
    limit = int(giveaway.get("limit", 0))

    lines = [
        "🎁 <b>GIVEAWAY</b>",
        "",
        f"👤 {_giveaway_mention(giveaway.get('organizer_id'), giveaway.get('organizer_name'))} tomonidan",
        f"🎁 Sovg‘a: {_giveaway_amount_text(int(giveaway.get('amount', 0)), giveaway.get('currency', 'pul'))}",
        f"👥 Qatnashchilar: {len(participants)}/{limit}",
        "",
        "🎟️ <b>QATNASHISH</b>",
        "👥 <b>Qatnashganlar:</b>",
    ]

    if not participants:
        lines.append("📭 Hali hech kim qo‘shilmadi.")
    else:
        for i, item in enumerate(participants, 1):
            lines.append(
                f"{i}. {_giveaway_mention(item['id'], item.get('name', 'O‘yinchi'))}"
            )

    return "\n".join(lines)


async def giveaway_command(update, context):
    """🎁 Giveaway boshlash."""

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text(
            "❌ /giveaway faqat guruhda ishlaydi."
        )
        return

    context.user_data["giveaway_setup"] = {
        "chat_id": int(chat.id),
        "chat_title": chat.title or "Guruh",
        "organizer_id": int(user.id),
        "organizer_name": _giveaway_name(user),
        "step": "limit",
    }

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "🎁 <b>GIVEAWAY SOZLASH</b>\n\n"
                f"👥 Guruh: <b>{html.escape(chat.title or 'Guruh')}</b>\n\n"
                "👥 Qatnashchilar limitini tanlang:"
            ),
            parse_mode="HTML",
            reply_markup=_giveaway_limit_keyboard(),
        )
    except Exception:
        context.user_data.pop("giveaway_setup", None)
        await message.reply_text(
            "❌ Sizga shaxsiy xabar yubora olmadim.\n\n"
            "🤖 Avval botga /start yuboring."
        )
        return

    await message.reply_text(
        "🎁 Giveaway sozlamalari shaxsiy xabaringizga yuborildi. 📩"
    )


async def giveaway_private_text(update, context):
    """📩 Giveaway DM orqali miqdor kiritish."""

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    if chat.type != "private":
        return

    setup = context.user_data.get("giveaway_setup")

    if not isinstance(setup, dict):
        return

    if int(setup.get("organizer_id", 0)) != int(user.id):
        return

    if setup.get("step") == "limit_custom":
        try:
            limit = int((message.text or "").strip())
        except (TypeError, ValueError):
            await message.reply_text(
                "❌ Raqam kiriting.\n\n"
                "👥 Limit: 1–100"
            )
            return

        if not 1 <= limit <= 100:
            await message.reply_text(
                "❌ Limit 1–100 oralig‘ida bo‘lishi kerak."
            )
            return

        setup["limit"] = limit
        setup["step"] = "amount"

        await message.reply_text(
            "🎁 <b>Sovg‘a miqdorini kiriting:</b>\n\n"
            "Masalan: <code>10000</code>",
            parse_mode="HTML",
        )
        return

    if setup.get("step") == "amount":
        try:
            amount = int((message.text or "").strip())
        except (TypeError, ValueError):
            await message.reply_text(
                "❌ Miqdor raqam bo‘lishi kerak."
            )
            return

        if amount <= 0:
            await message.reply_text(
                "❌ Miqdor 0 dan katta bo‘lishi kerak."
            )
            return

        setup["amount"] = amount
        setup["step"] = "currency"

        await message.reply_text(
            "💰 <b>Valyutani tanlang:</b>",
            parse_mode="HTML",
            reply_markup=_giveaway_currency_keyboard(),
        )


async def giveaway_callback(update, context):
    """🎁 Giveaway callbacklari."""

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    data = query.data or ""

    if data == "giveaway_limit_custom":
        setup = context.user_data.get("giveaway_setup")

        if not isinstance(setup, dict):
            await query.answer(
                "❌ Giveaway sozlamasi topilmadi.",
                show_alert=True,
            )
            return

        setup["step"] = "limit_custom"
        await query.answer()

        await query.message.edit_text(
            "👥 <b>Qatnashchilar sonini yozing:</b>\n\n"
            "1–100 oralig‘ida.\n"
            "Masalan: <code>34</code>",
            parse_mode="HTML",
        )
        return

    if data.startswith("giveaway_limit:"):
        setup = context.user_data.get("giveaway_setup")

        if not isinstance(setup, dict):
            await query.answer(
                "❌ Giveaway sozlamasi topilmadi.",
                show_alert=True,
            )
            return

        try:
            limit = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await query.answer(
                "❌ Limit xatosi.",
                show_alert=True,
            )
            return

        setup["limit"] = limit
        setup["step"] = "amount"

        await query.answer()

        await query.message.edit_text(
            f"👥 Limit: <b>{limit}</b>\n\n"
            "🎁 <b>Sovg‘a miqdorini kiriting:</b>\n\n"
            "Masalan: <code>10000</code>",
            parse_mode="HTML",
        )
        return

    if data.startswith("giveaway_currency:"):
        setup = context.user_data.get("giveaway_setup")

        if not isinstance(setup, dict):
            await query.answer(
                "❌ Giveaway sozlamasi topilmadi.",
                show_alert=True,
            )
            return

        currency = data.split(":", 1)[1]

        if currency not in ("pul", "almas"):
            await query.answer(
                "❌ Valyuta xatosi.",
                show_alert=True,
            )
            return

        setup["currency"] = currency
        setup["step"] = "confirm"

        fee = 100 if currency == "pul" else 1
        amount = int(setup["amount"])
        total = amount + fee

        await query.answer()

        await query.message.edit_text(
            "🎁 <b>GIVEAWAY TASDIQLASH</b>\n\n"
            f"👥 Qatnashchilar: <b>{setup['limit']}</b>\n"
            f"🎁 Sovg‘a: <b>{_giveaway_amount_text(amount, currency)}</b>\n"
            f"💸 Komissiya: <b>{fee:,} {_giveaway_currency_short(currency)}</b>\n"
            f"🔻 Jami yechiladi: <b>{total:,} {_giveaway_currency_short(currency)}</b>",
            parse_mode="HTML",
            reply_markup=_giveaway_confirm_keyboard(),
        )
        return



# ==========================================================
# 🎁 GIVEAWAY SYSTEM V2 — YAKUNLASH + QATNASHISH
# ==========================================================

    if data == "giveaway_cancel":
        context.user_data.pop("giveaway_setup", None)

        await query.answer("❌ Bekor qilindi.")
        await query.message.edit_text(
            "❌ <b>GIVEAWAY BEKOR QILINDI</b>\n\n"
            "💰 Mablag‘ yechilmadi.",
            parse_mode="HTML",
        )
        return

    if data == "giveaway_confirm":
        setup = context.user_data.get("giveaway_setup")

        if not isinstance(setup, dict):
            await query.answer(
                "❌ Giveaway sozlamasi topilmadi.",
                show_alert=True,
            )
            return

        if int(setup.get("organizer_id", 0)) != int(user.id):
            await query.answer(
                "❌ Bu Giveaway sizniki emas.",
                show_alert=True,
            )
            return

        amount = int(setup.get("amount", 0))
        limit = int(setup.get("limit", 0))
        currency = setup.get("currency")

        if amount <= 0 or not 1 <= limit <= 100:
            await query.answer(
                "❌ Giveaway ma’lumotlari noto‘g‘ri.",
                show_alert=True,
            )
            return

        if currency not in ("pul", "almas"):
            await query.answer(
                "❌ Valyuta tanlanmagan.",
                show_alert=True,
            )
            return

        fee = 100 if currency == "pul" else 1
        total = amount + fee

        db = load_data()
        users = db.setdefault("users", {})
        organizer_id = str(user.id)
        organizer = users.get(organizer_id)

        if not isinstance(organizer, dict):
            await query.answer(
                "❌ Avval /start yuboring.",
                show_alert=True,
            )
            return

        balance_key = "pul" if currency == "pul" else "almas"
        balance = int(organizer.get(balance_key, 0))

        if balance < total:
            await query.answer(
                f"❌ Yetarli {_giveaway_currency_short(currency)} yo‘q.",
                show_alert=True,
            )
            return

        giveaway_id = uuid.uuid4().hex[:10]

        giveaway = {
            "id": giveaway_id,
            "status": "active",
            "chat_id": int(setup["chat_id"]),
            "chat_title": setup.get("chat_title", "Guruh"),
            "organizer_id": int(user.id),
            "organizer_name": _giveaway_name(user),
            "limit": limit,
            "amount": amount,
            "currency": currency,
            "fee": fee,
            "participants": [],
            "winner_id": None,
            "winner_name": None,
            "message_id": None,
        }

        try:
            sent = await context.bot.send_message(
                chat_id=int(setup["chat_id"]),
                text=_giveaway_text(giveaway),
                parse_mode="HTML",
                reply_markup=_giveaway_keyboard(giveaway_id),
            )
        except Exception as e:
            print("❌ GIVEAWAY GROUP XATOSI:", e)
            await query.answer(
                "❌ Guruhga e’lon yuborilmadi.",
                show_alert=True,
            )
            return

        giveaway["message_id"] = int(sent.message_id)

        organizer[balance_key] = balance - total
        users[organizer_id] = organizer

        db.setdefault("giveaways", {})
        db["giveaways"][giveaway_id] = giveaway
        save_data(db)

        context.user_data.pop("giveaway_setup", None)

        await query.answer("🎁 Giveaway boshlandi!")

        await query.message.edit_text(
            "🎉 <b>GIVEAWAY BOSHLANDI!</b>\n\n"
            f"👥 Limit: <b>{limit}</b>\n"
            f"🎁 Sovg‘a: <b>{_giveaway_amount_text(amount, currency)}</b>\n"
            f"💸 Komissiya: <b>{fee:,} {_giveaway_currency_short(currency)}</b>\n\n"
            "🛑 Giveaway tugaganda shu yerda "
            "to‘xtatish tugmasidan foydalaning.",
            parse_mode="HTML",
            reply_markup=_giveaway_stop_keyboard(giveaway_id),
        )
        return

    if data.startswith("giveaway_join:"):
        giveaway_id = data.split(":", 1)[1]
        lock = _giveaway_lock(giveaway_id)

        async with lock:
            db = load_data()
            giveaway = db.get("giveaways", {}).get(giveaway_id)

            if not isinstance(giveaway, dict):
                await query.answer(
                    "❌ Giveaway topilmadi.",
                    show_alert=True,
                )
                return

            if giveaway.get("status") != "active":
                await query.answer(
                    "🔒 Giveaway yakunlangan.",
                    show_alert=True,
                )
                return

            if int(user.id) == int(
                giveaway.get("organizer_id", 0)
            ):
                await query.answer(
                    "❌ Tashkilotchi qatnasha olmaydi.",
                    show_alert=True,
                )
                return

            participants = giveaway.setdefault(
                "participants", []
            )

            if any(
                int(x.get("id", 0)) == int(user.id)
                for x in participants
                if isinstance(x, dict)
            ):
                await query.answer(
                    "ℹ️ Siz allaqachon qatnashgansiz.",
                    show_alert=True,
                )
                return

            limit = int(giveaway.get("limit", 0))

            if len(participants) >= limit:
                await query.answer(
                    "🔒 Joylar to‘lgan.",
                    show_alert=True,
                )
                return

            participants.append({
                "id": int(user.id),
                "name": _giveaway_name(user),
            })

            db["giveaways"][giveaway_id] = giveaway
            save_data(db)

            try:
                await query.edit_message_text(
                    _giveaway_text(giveaway),
                    parse_mode="HTML",
                    reply_markup=_giveaway_keyboard(
                        giveaway_id,
                        full=len(participants) >= limit,
                    ),
                )
            except Exception as e:
                print("❌ GIVEAWAY UPDATE XATOSI:", e)

            await query.answer(
                "🎟️ Siz Giveawayga qo‘shildingiz!"
            )

        return

    if data.startswith("giveaway_stop:"):
        giveaway_id = data.split(":", 1)[1]
        lock = _giveaway_lock(giveaway_id)

        async with lock:
            db = load_data()
            giveaway = db.get("giveaways", {}).get(giveaway_id)

            if not isinstance(giveaway, dict):
                await query.answer(
                    "❌ Giveaway topilmadi.",
                    show_alert=True,
                )
                return

            if int(user.id) != int(
                giveaway.get("organizer_id", 0)
            ):
                await query.answer(
                    "❌ Faqat tashkilotchi to‘xtata oladi.",
                    show_alert=True,
                )
                return

            if giveaway.get("status") != "active":
                await query.answer(
                    "🔒 Giveaway allaqachon yopilgan.",
                    show_alert=True,
                )
                return

            participants = giveaway.setdefault(
                "participants", []
            )

            if not participants:
                giveaway["status"] = "closed"

                db["giveaways"][giveaway_id] = giveaway

                organizer_id = str(user.id)
                organizer = db.get("users", {}).get(
                    organizer_id
                )

                if isinstance(organizer, dict):
                    currency = giveaway["currency"]
                    refund = int(giveaway["amount"]) + int(
                        giveaway["fee"]
                    )
                    key = "pul" if currency == "pul" else "almas"
                    organizer[key] = (
                        int(organizer.get(key, 0))
                        + refund
                    )
                    db["users"][organizer_id] = organizer

                save_data(db)

                try:
                    await context.bot.edit_message_text(
                        chat_id=int(giveaway["chat_id"]),
                        message_id=int(giveaway["message_id"]),
                        text=(
                            "🎉 <b>GIVEAWAY YAKUNLANDI!</b>\n\n"
                            "📭 Qatnashchilar bo‘lmadi.\n"
                            "💰 Mablag‘ qaytarildi."
                        ),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

                await query.answer(
                    "📭 Qatnashchilar bo‘lmadi."
                )

                await query.message.edit_text(
                    "🎉 <b>GIVEAWAY YAKUNLANDI!</b>\n\n"
                    "📭 Qatnashchilar bo‘lmadi.\n"
                    "💰 Mablag‘ qaytarildi.",
                    parse_mode="HTML",
                )
                return

            winner = random.choice(participants)

            giveaway["status"] = "closed"
            giveaway["winner_id"] = int(winner["id"])
            giveaway["winner_name"] = winner.get(
                "name", "O‘yinchi"
            )

            currency = giveaway["currency"]
            amount = int(giveaway["amount"])
            winner_id = str(winner["id"])

            winner_user = db.get("users", {}).get(
                winner_id
            )

            if not isinstance(winner_user, dict):
                await query.answer(
                    "❌ G‘olib akkaunti topilmadi.",
                    show_alert=True,
                )
                return

            key = "pul" if currency == "pul" else "almas"

            winner_user[key] = (
                int(winner_user.get(key, 0)) + amount
            )

            db["users"][winner_id] = winner_user
            db["giveaways"][giveaway_id] = giveaway
            save_data(db)

            winner_mention = _giveaway_mention(
                winner["id"],
                winner.get("name", "O‘yinchi"),
            )

            final_text = (
                "🎉 <b>GIVEAWAY YAKUNLANDI!</b>\n\n"
                "🏆 <b>G‘OLIB:</b>\n"
                f"👤 {winner_mention}\n\n"
                f"🎁 Sovg‘a: <b>"
                f"{_giveaway_amount_text(amount, currency)}"
                f"</b>\n"
                f"👥 Qatnashchilar: <b>{len(participants)}</b>"
            )

            try:
                await context.bot.edit_message_text(
                    chat_id=int(giveaway["chat_id"]),
                    message_id=int(giveaway["message_id"]),
                    text=final_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                print("❌ GIVEAWAY FINAL XATOSI:", e)

            await query.answer(
                "🏆 Giveaway yakunlandi!"
            )

            await query.message.edit_text(
                final_text,
                parse_mode="HTML",
            )

            try:
                await context.bot.send_message(
                    chat_id=int(winner["id"]),
                    text=(
                        "🏆 <b>GIVEAWAYDA G‘OLIB BO‘LDINGIZ!</b>\n\n"
                        f"🎁 Sovg‘a: <b>"
                        f"{_giveaway_amount_text(amount, currency)}"
                        f"</b>\n\n"
                        "🎉 Tabriklaymiz!"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

        return


# ==========================================================
# 🎁 GIVEAWAY SYSTEM V2 MARKER
# ==========================================================

async def start_premium_groups_callback(update, context):
    query = update.callback_query
    await query.answer()

    data_store = load_data()
    groups = data_store.get("groups", {})
    now = datetime.now()

    buttons = []
    unavailable = 0

    for gid, group in groups.items():
        if not bool(group.get("premium_active", False)):
            continue

        premium_until = group.get("premium_until")

        # ♾️ Cheksiz Premium
        if premium_until is None:
            duration_text = "♾️ Cheksiz"
        else:
            try:
                expires_at = datetime.fromisoformat(str(premium_until))
            except (ValueError, TypeError):
                continue

            remaining = expires_at - now

            # ⛔ Muddati tugagan Premiumni ko‘rsatmaymiz
            if remaining.total_seconds() <= 0:
                continue

            total_seconds = int(remaining.total_seconds())
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60

            if days > 0:
                duration_text = f"⏳ {days} kun"
                if hours > 0:
                    duration_text += f" {hours} soat"
            elif hours > 0:
                duration_text = f"⏳ {hours} soat"
                if minutes > 0:
                    duration_text += f" {minutes} daqiqa"
            else:
                duration_text = f"⏳ {max(1, minutes)} daqiqa"

        title = str(group.get("title") or "Noma'lum guruh")
        invite_link = group.get("invite_link")

        # 🔗 Saqlangan invite link
        if not invite_link:
            try:
                chat = await context.bot.get_chat(int(gid))

                # 🌐 Ochiq guruh
                if getattr(chat, "username", None):
                    invite_link = f"https://t.me/{chat.username}"
                else:
                    # 🔐 Yopiq guruh — bot admin bo‘lsa invite link olamiz
                    invite = await context.bot.create_chat_invite_link(
                        chat_id=int(gid)
                    )
                    invite_link = invite.invite_link
            except Exception:
                unavailable += 1
                continue

        buttons.append([
            InlineKeyboardButton(
                f"💎 {title[:28]} — {duration_text}",
                url=invite_link,
            )
        ])

    if not buttons:
        text = (
            "💎 PREMIUM GURUHLAR\n\n"
            "Hozircha Premium guruhlar mavjud emas."
        )
        if unavailable:
            text += (
                "\n\nℹ️ Ayrim guruhlar uchun kirish havolasi "
                "mavjud emas yoki bot guruhni topa olmadi."
            )
    else:
        text = (
            "💎 PREMIUM GURUHLAR\n\n"
            "Premium faol bo‘lgan guruhlar:\n\n"
            "👇 Guruhga kirish uchun ustiga bosing:"
        )

    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )


async def setup_commands(application):
    commands = [
        BotCommand("game", "🎮 Jang ochish"),
            BotCommand("giveaway", "🎁 Giveaway boshlash"),
        BotCommand("setting", "⚙️ Jang sozlamalari"),
        BotCommand("start", "▶️ Jangni boshlash"),
        BotCommand("exit", "🚪 Jangdan chiqish"),
        BotCommand("stop", "🛑 Jangni to‘xtatish"),
    ]

    await application.bot.set_my_commands(
        commands,
        scope=BotCommandScopeAllGroupChats(),
    )

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida topilmadi.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(setup_commands)
        .build()
    )

    # 👥 Guruh TOP
    app.add_handler(
    CommandHandler(
    "topgr",
    top10_2_group_top_command,
    )
    )

    # 📅 Guruh TOP — 7 kun
    app.add_handler(
    CommandHandler(
    "topgr7",
    top10_2_group_top7_command,
    )
    )

    # 📅 Guruh TOP — 30 kun
    app.add_handler(
    CommandHandler(
    "topgr30",
    top10_2_group_top30_command,
    )
    )

    # 📋 Bot ishlagan guruhlar
    app.add_handler(
    CommandHandler(
    "groups",
    top10_2_groups_command,
    )
    )

    # 🏆 Reyting
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("top7", top7_command))
    app.add_handler(CommandHandler("top30", top30_command))
    app.add_handler(
        CallbackQueryHandler(
            global_top_callback,
            pattern=r"^global_top:",
        )
    )
    app.add_handler(CommandHandler("achievements", achievements_command))

    # 🏅 Achievementlar
    app.add_handler(
    CommandHandler(
    "achievements",
    achievements_command,
    )
    )

    # 👑 Admin
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("give", player_give))
    app.add_handler(CommandHandler("money", player_money))
    # 🎁 Giveaway
    app.add_handler(
        CommandHandler("giveaway", giveaway_command)
    )
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.TEXT
            & ~filters.COMMAND,
            giveaway_private_text,
        ),
        group=1,
    )
    app.add_handler(
        CallbackQueryHandler(
            giveaway_callback,
            pattern=r"^giveaway_",
        )
    )
    app.add_handler(CommandHandler("givepul", give_pul))
    app.add_handler(CommandHandler("givealmas", give_almas))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("setreward", set_reward))
    app.add_handler(CommandHandler("setbonus", set_bonus))
    app.add_handler(CommandHandler("setstreak", set_streak))

    # 🛒 Magazin
    app.add_handler(CommandHandler("shop", shop_command))
    app.add_handler(CommandHandler("shopadd", shop_add_command))
    app.add_handler(CommandHandler("shopdel", shop_delete_command))
    app.add_handler(CommandHandler("shopprice", shop_price_command))

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🛒 Magazin$"),
            shop_command,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            shop_callback,
            pattern=r"^shop_",
        )
    )

    # 🎮 O‘yin
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("inventory", inventory_command))

    # 👑 Admin Panel tugmasi
    # Faqat Admin Panel Reply tugmasini ushlaydi.
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^👑 Admin Panel\s*$"),
            admin_command,
        )
    )
    app.add_handler(CommandHandler("game", game_command))
    app.add_handler(CommandHandler("setting", setting_command))
    app.add_handler(CommandHandler("settinghelp", settinghelp_command))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("warns", warns_command))
    app.add_handler(CommandHandler("delwarn", delwarn_command))
    app.add_handler(CommandHandler("resetwarns", resetwarns_command))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unmute", unmute_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("kick", kick_command))
    app.add_handler(CommandHandler("adminn", adminn_command))
    app.add_handler(CommandHandler("unadminn", unadminn_command))

    app.add_handler(CommandHandler("del", del_command))
    app.add_handler(CommandHandler("purge", purge_command))
    app.add_handler(CommandHandler("pin", pin_command))
    app.add_handler(CommandHandler("unpin", unpin_command))

    app.add_handler(CallbackQueryHandler(adminn_callback, pattern=r"^adminright:"))
    app.add_handler(CommandHandler("start", group_start_command))
    app.add_handler(CommandHandler("exit", exit_game))
    app.add_handler(CommandHandler("stop", stop_game))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r"^👤 Profil$"),
            profile_command,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            topup_admin_callback,
            pattern=r"^topup_(accept|reject):"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            topup_start_callback,
            pattern=r"^profile_topup:(almas|pul)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            profile_callback,
            pattern=r"^profile_(refresh|shop)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            inventory_callback,
            pattern=r"^inventory_"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.TEXT
            & ~filters.COMMAND,
            topup_amount_handler,
        ),
        group=0,
    )

    # 🛒 Magazin admin kiritishlari
    # Alohida group=1: mavjud text handlerlarga xalaqit bermaydi.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_shop_text_handler,
        ),
        group=1,
    )

    # 🌊 Anti-Flood — group=2
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            antiflood_message,
        ),
        group=2,
    )

        # 🔗 Anti-Link — group=3
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            antilink_message,
        ),
        group=3,
    )

    # 📢 Anti-Reklama — group=4
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            antireklama_message,
        ),
        group=4,
    )

    # 🔁 Anti-Repeat — group=5
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            antirepeat_message,
        ),
        group=5,
    )

    # 🔠 Anti-Caps — group=6
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            anticaps_message,
        ),
        group=6,
    )

    # 👥 Anti-Mention — group=7
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            antimention_message,
        ),
        group=7,
    )

    # 🎯 Callbacklar
    # 💎 Premium guruhlar
    app.add_handler(
        CallbackQueryHandler(
            start_premium_groups_callback,
            pattern=r"^start_premium_groups$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            moderation_callback,
            pattern=r"^mod(open|page|back|close|menu)(:|$)",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            setting_callback,
            pattern=r"^setting_timer:",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            handle_side_selection,
            pattern=r"^game_side_",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            start_game,
            pattern=r"^game_start$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            battle_callback,
            pattern=r"^battle_",
        )
    )

    # 🎯 Raqibni tanlash
    app.add_handler(
        CallbackQueryHandler(
            battle_callback,
            pattern=r"^attack_target:",
        )
    )

    # 🔫 Qurol tanlash
    app.add_handler(
        CallbackQueryHandler(
            battle_callback,
            pattern=r"^weapon:",
        )
    )

    print("🚀 Bot ishga tushmoqda...")
    app.run_polling()




# ==================================================
# 🤖 BOT.PY FUNKSIYALARI — MAIN.PY GA KO‘CHIRILDI
# ==================================================

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
        ],
        [
            InlineKeyboardButton(
                "🛒 Magazin boshqaruvi",
                callback_data="admin_shop"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 Premium boshqaruvi",
                callback_data="admin_premium"
            )
        ]
    ])


async def _send_global_top(update, days=None):
    """🌍 Global TOP — barcha guruhlarni birlashtiradi."""
    rows = player_top(limit=100, days=days)

    period_name = {
        None: "ALL",
        7: "7 KUN",
        30: "30 KUN",
    }.get(days, "ALL")

    page_size = 20
    total_pages = max(
        1,
        min(5, (len(rows) + page_size - 1) // page_size),
    )

    page = 1
    page_rows = rows[:page_size]

    text = format_player_top(
        page_rows,
        period_name,
        start_rank=1,
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "◀️",
                callback_data=f"global_top:{days if days is not None else 'all'}:1",
            ),
            InlineKeyboardButton(
                f"📄 1/{total_pages}",
                callback_data="global_top:noop",
            ),
            InlineKeyboardButton(
                "▶️",
                callback_data=f"global_top:{days if days is not None else 'all'}:2",
            ),
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=markup,
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=markup,
        )


async def _top_access(update):
    """🔐 TOP ruxsati."""

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return False, False

    # 🤖 Bot admini hamma TOPni ko‘ra oladi.
    try:
        if is_admin(user.id):
            return True, True
    except Exception:
        pass

    # 👥 Guruhda faqat shu guruh admini ko‘ra oladi.
    if chat.type in ("group", "supergroup"):
        try:
            return (
                await is_group_admin(update, user.id),
                False,
            )
        except Exception:
            return False, False

    # 🔒 Private chat — faqat bot admini.
    return False, False


async def _send_global_top(update, days=None):
    """🌍 Private chatdagi global TOP 100."""

    allowed, _ = await _top_access(update)

    if not allowed:
        if update.message:
            await update.message.reply_text(
                "🔒 Bu TOPni faqat 🤖 bot administratori ko‘ra oladi."
            )
        return

    rows = player_top(
        limit=100,
        days=days,
    )

    period_name = {
        None: "ALL",
        7: "7 KUN",
        30: "30 KUN",
    }.get(days, "ALL")

    page_size = 20
    total_pages = max(
        1,
        min(
            5,
            (len(rows) + page_size - 1) // page_size,
        ),
    )

    text = format_player_top(
        rows[:page_size],
        period_name,
        start_rank=1,
    )

    period = (
        "all"
        if days is None
        else str(days)
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "◀️",
                callback_data=f"global_top:{period}:1",
            ),
            InlineKeyboardButton(
                f"📄 1/{total_pages}",
                callback_data="global_top:noop",
            ),
            InlineKeyboardButton(
                "▶️",
                callback_data=f"global_top:{period}:2",
            ),
        ]
    ]

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def _send_group_player_top(update, days=None):
    """👥 Faqat shu guruhning o‘yinchilari TOP 30."""

    allowed, _ = await _top_access(update)

    if not allowed:
        if update.message:
            await update.message.reply_text(
                "🔒 Bu TOPni faqat 👑 guruh administratori yoki 🤖 bot administratori ko‘ra oladi."
            )
        return

    chat = update.effective_chat

    if not chat or chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "👥 Bu TOP faqat guruh ichida ishlaydi."
        )
        return

    data = load_data()

    rows = group_player_top(
        data,
        chat.id,
        limit=30,
        days=days,
    )

    period_name = {
        None: "ALL",
        7: "7 KUN",
        30: "30 KUN",
    }.get(days, "ALL")

    text = format_group_player_top(
        rows,
        period_name,
    )

    await update.message.reply_text(text)


async def top_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """🏆 /top — guruhda guruh TOPi, private'da global TOP."""
    chat = update.effective_chat

    if chat and chat.type in ("group", "supergroup"):
        await _send_group_player_top(update, None)
    else:
        await _send_global_top(update, None)


async def top7_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """📅 /top7."""
    chat = update.effective_chat

    if chat and chat.type in ("group", "supergroup"):
        await _send_group_player_top(update, 7)
    else:
        await _send_global_top(update, 7)


async def top30_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """📆 /top30."""
    chat = update.effective_chat

    if chat and chat.type in ("group", "supergroup"):
        await _send_group_player_top(update, 30)
    else:
        await _send_global_top(update, 30)


async def global_top_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """🔘 Global TOP pagination."""

    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    # 🔒 Faqat bot admini global TOP paginationini ko‘ra oladi.
    user = update.effective_user

    try:
        if not is_admin(user.id):
            await query.answer(
                "🔒 Faqat 🤖 bot administratori.",
                show_alert=True,
            )
            return
    except Exception:
        return

    data = query.data or ""

    if data == "global_top:noop":
        return

    try:
        _, period, page_text = data.split(":", 2)
        page = int(page_text)
    except (ValueError, TypeError):
        return

    days = {
        "all": None,
        "7": 7,
        "30": 30,
    }.get(period)

    rows = player_top(
        limit=100,
        days=days,
    )

    page_size = 20

    total_pages = max(
        1,
        min(
            5,
            (len(rows) + page_size - 1) // page_size,
        ),
    )

    page = max(
        1,
        min(page, total_pages),
    )

    start_rank = (
        (page - 1) * page_size
    )

    page_rows = rows[
        start_rank:start_rank + page_size
    ]

    period_name = {
        None: "ALL",
        7: "7 KUN",
        30: "30 KUN",
    }.get(days, "ALL")

    text = format_player_top(
        page_rows,
        period_name,
        start_rank=start_rank + 1,
    )

    previous_page = max(
        1,
        page - 1,
    )

    next_page = min(
        total_pages,
        page + 1,
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "◀️",
                callback_data=f"global_top:{period}:{previous_page}",
            ),
            InlineKeyboardButton(
                f"📄 {page}/{total_pages}",
                callback_data="global_top:noop",
            ),
            InlineKeyboardButton(
                "▶️",
                callback_data=f"global_top:{period}:{next_page}",
            ),
        ]
    ]

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        print(
            f"❌ GLOBAL TOP CALLBACK XATOSI: {e}"
        )


# ============================================================
# 🔟 10.2 — TOP KOMANDALAR
# ============================================================

async def top10_2_group_access(update):
    """🔐 Guruh TOP komandalariga ruxsat."""

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return False

    # 🤖 Bot admin
    try:
        if is_admin(user.id):
            return True
    except Exception:
        pass

    # 👤 Private chatda guruh TOP yo‘q
    if chat.type == "private":
        return False

    # 👑 Guruh admini
    try:
        return await is_group_admin(
            update,
            user.id,
        )
    except Exception:
        return False


async def top10_2_group_top_command(
    update,
    context,
):
    """👥 Barcha guruhlarning bugungi TOP'i."""
    try:
        from top_stats import group_top, format_group_top

        rows = group_top(limit=30, days=1)

        if not rows:
            text = (
                "👥 GURUH TOP — BUGUN\n"
                "━━━━━━━━━━━━━━━━\n"
                "📭 Bugun statistika yo‘q."
            )
        else:
            text = format_group_top(rows, "BUGUN")

        await update.message.reply_text(text)

    except Exception as e:
        print(f"❌ /topgr xatosi: {e}")
        await update.message.reply_text(
            "❌ Guruh TOPni olishda xatolik yuz berdi."
        )


async def top10_2_group_top7_command(
    update,
    context,
):
    """📅 Barcha guruhlarning 7 kunlik TOP'i."""
    try:
        from top_stats import group_top, format_group_top

        rows = group_top(limit=30, days=7)

        if not rows:
            text = (
                "📅 GURUH TOP — 7 KUN\n"
                "━━━━━━━━━━━━━━━━\n"
                "📭 Oxirgi 7 kunda statistika yo‘q."
            )
        else:
            text = format_group_top(rows, "7 KUN")

        await update.message.reply_text(text)

    except Exception as e:
        print(f"❌ /topgr7 xatosi: {e}")
        await update.message.reply_text(
            "❌ 7 kunlik guruh TOPida xatolik."
        )


async def top10_2_group_top30_command(
    update,
    context,
):
    """📅 Barcha guruhlarning 30 kunlik TOP'i."""
    try:
        from top_stats import group_top, format_group_top

        rows = group_top(limit=30, days=30)

        if not rows:
            text = (
                "📅 GURUH TOP — 30 KUN\n"
                "━━━━━━━━━━━━━━━━\n"
                "📭 Oxirgi 30 kunda statistika yo‘q."
            )
        else:
            text = format_group_top(rows, "30 KUN")

        await update.message.reply_text(text)

    except Exception as e:
        print(f"❌ /topgr30 xatosi: {e}")
        await update.message.reply_text(
            "❌ 30 kunlik guruh TOPida xatolik."
        )


async def top10_2_groups_command(
    update,
    context,
):
    """📋 Bot ishlagan barcha guruhlar."""

    user = update.effective_user

    try:
        if not is_admin(user.id):
            await update.message.reply_text(
                "🔒 /groups faqat bot admini uchun."
            )
            return
    except Exception:
        await update.message.reply_text(
            "🔒 /groups faqat bot admini uchun."
        )
        return

    try:
        from top_stats import all_groups, format_groups

        rows = all_groups(
            limit=1000
        )

        if not rows:
            await update.message.reply_text(
                "📋 GURUHLAR\n"
                "━━━━━━━━━━━━━━━━\n"
                "📭 Hali saqlangan guruh yo‘q."
            )
            return

        await update.message.reply_text(
            format_groups(rows)
        )

    except Exception as e:
        print(
            f"❌ /groups xatosi: {e}"
        )
        await update.message.reply_text(
            "❌ Guruhlar ro‘yxatini olishda xatolik."
        )



async def achievements_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """🏅 Foydalanuvchi achievementlari"""
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        ensure_user(user_id)
        user = get_user(user_id)

    await update.message.reply_text(
        achievements_text(user),
    )


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

    # 🛒 Magazin boshqaruvi
    if data == "admin_shop" or data.startswith("admin_shop_"):
        await admin_shop_callback(update, context)
        return

    if data.startswith("admin_premium:grantplan:"):
        parts = data.split(":", 3)
        if len(parts) != 4:
            await query.answer("❌ Noto‘g‘ri Premium so‘rovi.", show_alert=True)
            return

        group_id = parts[2]
        plan_key = parts[3]

        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))
        plans = data_store.get("settings", {}).get("premium_plans", {})
        plan = plans.get(plan_key)

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        if not plan:
            await query.answer("❌ Premium rejasi topilmadi.", show_alert=True)
            return

        days = plan.get("days")
        now = datetime.now()

        group["premium_active"] = True
        group["premium_plan"] = plan_key

        if days is None:
            group["premium_until"] = None
            duration_text = "♾️ Cheksiz"
        else:
            until = now + timedelta(days=int(days))
            group["premium_until"] = until.isoformat(timespec="seconds")
            duration_text = until.strftime("%Y-%m-%d %H:%M:%S")

        save_data(data_store)

        await query.message.reply_text(
            "💎 PREMIUM BERILDI\n\n"
            f"👥 Guruh: {group.get('title') or 'Noma\'lum guruh'}\n"
            f"📦 Reja: {plan.get('name', plan_key)}\n"
            f"⏳ Tugash: {duration_text}\n\n"
            "✅ Premium muvaffaqiyatli faollashtirildi."
        )
        return

    if data.startswith("admin_premium:grant:"):
        group_id = data.split(":", 2)[2]
        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        plans = data_store.get("settings", {}).get("premium_plans", {})
        buttons = []

        for plan_key, plan in plans.items():
            name = str(plan.get("name", plan_key))
            price = int(plan.get("price", 0))
            buttons.append([
                InlineKeyboardButton(
                    f"{name} — 💎 {price}",
                    callback_data=f"admin_premium:grantplan:{group_id}:{plan_key}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "🔙 Guruh",
                callback_data=f"admin_premium:group:{group_id}"
            )
        ])

        await query.message.reply_text(
            f"➕ PREMIUM BERISH\n\n"
            f"👥 {group.get('title') or 'Noma\'lum guruh'}\n\n"
            "Muddatni tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("admin_premium:extendplan:"):
        parts = data.split(":", 3)
        if len(parts) != 4:
            await query.answer("❌ Noto‘g‘ri Premium so‘rovi.", show_alert=True)
            return

        group_id = parts[2]
        plan_key = parts[3]

        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))
        plans = data_store.get("settings", {}).get("premium_plans", {})
        plan = plans.get(plan_key)

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        if not plan:
            await query.answer("❌ Premium rejasi topilmadi.", show_alert=True)
            return

        days = plan.get("days")
        now = datetime.now()

        group["premium_active"] = True

        if days is None:
            group["premium_plan"] = plan_key
            group["premium_until"] = None
            duration_text = "♾️ Cheksiz"
        else:
            old_until = group.get("premium_until")
            base_time = now

            if old_until:
                try:
                    parsed_until = datetime.fromisoformat(str(old_until))
                    if parsed_until > now:
                        base_time = parsed_until
                except (ValueError, TypeError):
                    base_time = now

            until = base_time + timedelta(days=int(days))
            group["premium_until"] = until.isoformat(timespec="seconds")
            group["premium_plan"] = plan_key
            duration_text = until.strftime("%Y-%m-%d %H:%M:%S")

        save_data(data_store)

        await query.message.reply_text(
            "⏳ PREMIUM MUDDATI UZAYTIRILDI\n\n"
            f"👥 Guruh: {group.get('title') or 'Noma\'lum guruh'}\n"
            f"➕ Qo‘shildi: {plan.get('name', plan_key)}\n"
            f"⏳ Yangi tugash: {duration_text}\n\n"
            "✅ Muvaffaqiyatli saqlandi."
        )
        return

    if data.startswith("admin_premium:extend:"):
        group_id = data.split(":", 2)[2]
        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        plans = data_store.get("settings", {}).get("premium_plans", {})
        buttons = []

        for plan_key, plan in plans.items():
            name = str(plan.get("name", plan_key))
            buttons.append([
                InlineKeyboardButton(
                    name,
                    callback_data=f"admin_premium:extendplan:{group_id}:{plan_key}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "🔙 Guruh",
                callback_data=f"admin_premium:group:{group_id}"
            )
        ])

        await query.message.reply_text(
            "⏳ PREMIUM MUDDATINI UZAYTIRISH\n\n"
            f"👥 Guruh: {group.get('title') or 'Noma\'lum guruh'}\n\n"
            "Qo‘shiladigan muddatni tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("admin_premium:status:"):
        group_id = data.split(":", 2)[2]
        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        title = str(group.get("title") or "Noma'lum guruh")
        premium_active = bool(group.get("premium_active", False))
        premium_plan = group.get("premium_plan")
        premium_until = group.get("premium_until")

        if premium_active and premium_until:
            try:
                until = datetime.fromisoformat(str(premium_until))
                now = datetime.now()
                remaining = until - now

                if remaining.total_seconds() <= 0:
                    group["premium_active"] = False
                    group["premium_plan"] = None
                    group["premium_until"] = None
                    save_data(data_store)

                    premium_text = "❌ Muddati tugagan"
                    remaining_text = "0 kun"
                else:
                    total_seconds = int(remaining.total_seconds())
                    days = total_seconds // 86400
                    hours = (total_seconds % 86400) // 3600
                    minutes = (total_seconds % 3600) // 60

                    premium_text = "💎 Faol"
                    remaining_text = (
                        f"🕐 {days} kun, {hours} soat, {minutes} daqiqa"
                    )
            except (ValueError, TypeError):
                premium_text = "⚠️ Muddat ma'lumotida xato"
                remaining_text = "❓ Aniqlab bo‘lmadi"
        elif premium_active:
            premium_text = "💎 Faol"
            remaining_text = "♾️ Cheksiz"
        else:
            premium_text = "❌ Faol emas"
            remaining_text = "—"

        await query.message.reply_text(
            "📊 PREMIUM HOLATI\n\n"
            f"👥 Guruh: {title}\n"
            f"🆔 ID: {group_id}\n"
            f"📦 Reja: {premium_plan or 'Yo‘q'}\n"
            f"📊 Holat: {premium_text}\n"
            f"⏳ Tugash: {premium_until or '♾️ Cheksiz' if premium_active else '—'}\n"
            f"🕐 Qolgan vaqt: {remaining_text}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Guruh",
                        callback_data=f"admin_premium:group:{group_id}"
                    )
                ]
            ])
        )
        return

    if data.startswith("admin_premium:group:"):
        group_id = data.split(":", 2)[2]
        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        title = str(group.get("title") or "Noma'lum guruh")
        premium_active = bool(group.get("premium_active", False))
        premium_plan = group.get("premium_plan")
        premium_until = group.get("premium_until")

        if premium_active:
            if premium_until:
                premium_text = f"💎 Faol\n⏳ Tugash: {premium_until}"
            else:
                premium_text = "💎 Faol\n♾️ Cheksiz"
        else:
            premium_text = "❌ Faol emas"

        await query.message.reply_text(
            f"👥 GURUH\n\n"
            f"🏷️ Nomi: {title}\n"
            f"🆔 ID: {group_id}\n"
            f"📦 Reja: {premium_plan or 'Yo‘q'}\n"
            f"📊 Holat: {premium_text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "➕ Premium berish",
                    callback_data=f"admin_premium:grant:{group_id}"
                )],
                [InlineKeyboardButton(
                    "⏳ Muddatni uzaytirish",
                    callback_data=f"admin_premium:extend:{group_id}"
                )],
                [InlineKeyboardButton(
                    "📊 Premium holati",
                    callback_data=f"admin_premium:status:{group_id}"
                )],
                [InlineKeyboardButton(
                    "❌ Premiumni bekor qilish",
                    callback_data=f"admin_premium:cancel:{group_id}"
                )],
                [InlineKeyboardButton(
                    "🔄 Muddatni yangilash",
                    callback_data=f"admin_premium:renew:{group_id}"
                )],
                [InlineKeyboardButton(
                    "🔙 Guruhlar",
                    callback_data="admin_premium:groups"
                )],
            ])
        )
        return

    if data.startswith("admin_premium:cancel:"):
        group_id = data.split(":", 2)[2]
        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        group["premium_active"] = False
        group["premium_plan"] = None
        group["premium_until"] = None

        save_data(data_store)

        await query.message.reply_text(
            "❌ PREMIUM BEKOR QILINDI\n\n"
            f"👥 Guruh: {group.get('title') or 'Noma\'lum guruh'}\n"
            "💎 Premium darhol o‘chirildi.\n"
            "✅ O‘zgarish saqlandi.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Guruh",
                        callback_data=f"admin_premium:group:{group_id}"
                    )
                ]
            ])
        )
        return

    if data.startswith("admin_premium:renewplan:"):
        parts = data.split(":", 3)
        if len(parts) != 4:
            await query.answer("❌ Noto‘g‘ri Premium so‘rovi.", show_alert=True)
            return

        group_id = parts[2]
        plan_key = parts[3]

        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))
        plans = data_store.get("settings", {}).get("premium_plans", {})
        plan = plans.get(plan_key)

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        if not plan:
            await query.answer("❌ Premium rejasi topilmadi.", show_alert=True)
            return

        days = plan.get("days")
        now = datetime.now()

        group["premium_active"] = True
        group["premium_plan"] = plan_key

        if days is None:
            group["premium_until"] = None
            duration_text = "♾️ Cheksiz"
        else:
            until = now + timedelta(days=int(days))
            group["premium_until"] = until.isoformat(timespec="seconds")
            duration_text = until.strftime("%Y-%m-%d %H:%M:%S")

        save_data(data_store)

        await query.message.reply_text(
            "🔄 PREMIUM MUDDATI YANGILANDI\n\n"
            f"👥 Guruh: {group.get('title') or 'Noma\'lum guruh'}\n"
            f"📦 Yangi reja: {plan.get('name', plan_key)}\n"
            f"⏳ Yangi tugash: {duration_text}\n\n"
            "✅ Muddat hozirgi vaqtdan qayta hisoblandi."
        )
        return

    if data.startswith("admin_premium:renew:"):
        group_id = data.split(":", 2)[2]
        data_store = load_data()
        groups = data_store.get("groups", {})
        group = groups.get(str(group_id))

        if not group:
            await query.answer("❌ Guruh topilmadi.", show_alert=True)
            return

        plans = data_store.get("settings", {}).get("premium_plans", {})
        buttons = []

        for plan_key, plan in plans.items():
            name = str(plan.get("name", plan_key))
            buttons.append([
                InlineKeyboardButton(
                    name,
                    callback_data=f"admin_premium:renewplan:{group_id}:{plan_key}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "🔙 Guruh",
                callback_data=f"admin_premium:group:{group_id}"
            )
        ])

        await query.message.reply_text(
            "🔄 PREMIUM MUDDATINI YANGILASH\n\n"
            f"👥 Guruh: {group.get('title') or 'Noma\'lum guruh'}\n\n"
            "Yangi muddatni tanlang:\n"
            "ℹ️ Muddat hozirgi vaqtdan qayta hisoblanadi.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # 💎 Premium amallari uchun avval guruh tanlash
    if data in {
        "admin_premium:extend",
        "admin_premium:status",
        "admin_premium:cancel",
        "admin_premium:renew",
    }:
        await query.message.reply_text(
            "👥 GURUHNI TANLANG\n\n"
            "Quyidagi guruhdan Premium amalini bajarish uchun guruhni tanlang:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        f"{'💎' if bool(group.get('premium_active', False)) else '👥'} {str(group.get('title') or 'Noma\'lum guruh')[:35]}",
                        callback_data=f"admin_premium:group:{gid}",
                    )
                ]
                for gid, group in load_data().get("groups", {}).items()
            ] + [
                [InlineKeyboardButton("🔙 Premium boshqaruvi", callback_data="admin_premium")]
            ]),
        )
        return

    if data == "admin_premium:groups":
        data_store = load_data()
        groups = data_store.get("groups", {})

        buttons = []
        for gid, group in groups.items():
            title = str(group.get("title") or "Noma'lum guruh")
            premium_active = bool(group.get("premium_active", False))
            icon = "💎" if premium_active else "👥"
            buttons.append([
                InlineKeyboardButton(
                    f"{icon} {title[:35]}",
                    callback_data=f"admin_premium:group:{gid}"
                )
            ])

        if not buttons:
            text = "👥 Guruhlar\n\nHozircha guruh topilmadi."
        else:
            text = f"👥 GURUHLAR\n\nJami: {len(groups)} ta guruh"

        buttons.append([
            InlineKeyboardButton(
                "🔙 Premium boshqaruvi",
                callback_data="admin_premium"
            )
        ])

        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data == "admin_premium:add":
        context.user_data["admin_premium_state"] = "add_group"

        await query.message.reply_text(
            "➕ PREMIUM GURUH QO‘SHISH\n\n"
            "👥 Guruh ID sini yuboring:\n\n"
            "Masalan:\n"
            "-1003555098763"
        )
        return

    if data == "admin_premium":
        await query.message.reply_text(
            "💎 PREMIUM GURUHLAR\n\n"
            "Premium guruhlarni boshqarish bo‘limi:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 Guruhlar", callback_data="admin_premium:groups")],
                [InlineKeyboardButton("➕ Premium berish", callback_data="admin_premium:add")],
                [InlineKeyboardButton("⏳ Muddatni uzaytirish", callback_data="admin_premium:extend")],
                [InlineKeyboardButton("📊 Premium holati", callback_data="admin_premium:status")],
                [InlineKeyboardButton("❌ Premiumni bekor qilish", callback_data="admin_premium:cancel")],
                [InlineKeyboardButton("🔄 Muddatni yangilash", callback_data="admin_premium:renew")],
            ]),
        )
        return

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

async def player_give(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """🔷 O‘yinchilar o‘zaro Almas yuborishi."""

    message = update.effective_message
    chat = update.effective_chat
    sender = update.effective_user

    if not message or not chat or not sender:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text(
            "❌ Bu buyruq faqat guruhda ishlaydi."
        )
        return

    replied = message.reply_to_message
    if not replied or not replied.from_user:
        await message.reply_text(
            "↩️ Almas yuborish uchun o‘yinchining "
            "xabariga Reply qiling.\n\n"
            "🔷 /give 5"
        )
        return

    target = replied.from_user

    if target.is_bot:
        await message.reply_text("❌ Botga Almas yuborib bo‘lmaydi.")
        return

    if int(target.id) == int(sender.id):
        await message.reply_text(
            "❌ O‘zingizga Almas yubora olmaysiz."
        )
        return

    args = list(context.args or [])

    if len(args) != 1:
        await message.reply_text(
            "❌ Format:\n🔷 /give MIQDOR"
        )
        return

    try:
        amount = int(args[0])
    except (TypeError, ValueError):
        await message.reply_text(
            "❌ Miqdor raqam bo‘lishi kerak."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Miqdor 0 dan katta bo‘lishi kerak."
        )
        return

    data = load_data()
    users = data.setdefault("users", {})

    sender_id = str(sender.id)
    target_id = str(target.id)

    sender_user = users.get(sender_id)
    target_user = users.get(target_id)

    if not isinstance(sender_user, dict):
        await message.reply_text(
            "❌ Avval /start yuboring."
        )
        return

    if not isinstance(target_user, dict):
        await message.reply_text(
            "❌ Bu o‘yinchi hali botda ro‘yxatdan o‘tmagan."
        )
        return

    fee = 1
    total = amount + fee
    balance = int(sender_user.get("almas", 0))

    if balance < total:
        await message.reply_text(
            "❌ Almas balansingiz yetarli emas.\n\n"
            f"🔷 Yuboriladi: {amount:,} Almas\n"
            f"💸 Komissiya: {fee:,} Almas\n"
            f"🔷 Jami kerak: {total:,} Almas\n"
            f"👛 Balansingiz: {balance:,} Almas"
        )
        return

    sender_user["almas"] = balance - total
    target_user["almas"] = int(target_user.get("almas", 0)) + amount

    users[sender_id] = sender_user
    users[target_id] = target_user
    save_data(data)

    sender_name = sender.first_name or "O‘yinchi"
    target_name = target.first_name or "O‘yinchi"

    await message.reply_text(
        "🔷 ALMAS YUBORILDI!\n\n"
        f"👤 {sender_name} ➡️ {target_name}\n"
        f"🔷 Qabul qilindi: {amount:,} Almas\n"
        f"💸 Komissiya: {fee:,} Almas\n"
        f"🔷 Jami yechildi: {total:,} Almas"
    )


async def player_money(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """🪙 O‘yinchilar o‘zaro Pul yuborishi."""

    message = update.effective_message
    chat = update.effective_chat
    sender = update.effective_user

    if not message or not chat or not sender:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text(
            "❌ Bu buyruq faqat guruhda ishlaydi."
        )
        return

    replied = message.reply_to_message
    if not replied or not replied.from_user:
        await message.reply_text(
            "↩️ Pul yuborish uchun o‘yinchining "
            "xabariga Reply qiling.\n\n"
            "🪙 /money 500"
        )
        return

    target = replied.from_user

    if target.is_bot:
        await message.reply_text("❌ Botga Pul yuborib bo‘lmaydi.")
        return

    if int(target.id) == int(sender.id):
        await message.reply_text(
            "❌ O‘zingizga Pul yubora olmaysiz."
        )
        return

    args = list(context.args or [])

    if len(args) != 1:
        await message.reply_text(
            "❌ Format:\n🪙 /money MIQDOR"
        )
        return

    try:
        amount = int(args[0])
    except (TypeError, ValueError):
        await message.reply_text(
            "❌ Miqdor raqam bo‘lishi kerak."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Miqdor 0 dan katta bo‘lishi kerak."
        )
        return

    data = load_data()
    users = data.setdefault("users", {})

    sender_id = str(sender.id)
    target_id = str(target.id)

    sender_user = users.get(sender_id)
    target_user = users.get(target_id)

    if not isinstance(sender_user, dict):
        await message.reply_text(
            "❌ Avval /start yuboring."
        )
        return

    if not isinstance(target_user, dict):
        await message.reply_text(
            "❌ Bu o‘yinchi hali botda ro‘yxatdan o‘tmagan."
        )
        return

    fee = 100
    total = amount + fee
    balance = int(sender_user.get("pul", 0))

    if balance < total:
        await message.reply_text(
            "❌ Pul balansingiz yetarli emas.\n\n"
            f"🪙 Yuboriladi: {amount:,} Pul\n"
            f"💸 Komissiya: {fee:,} Pul\n"
            f"🪙 Jami kerak: {total:,} Pul\n"
            f"👛 Balansingiz: {balance:,} Pul"
        )
        return

    sender_user["pul"] = balance - total
    target_user["pul"] = int(target_user.get("pul", 0)) + amount

    users[sender_id] = sender_user
    users[target_id] = target_user
    save_data(data)

    sender_name = sender.first_name or "O‘yinchi"
    target_name = target.first_name or "O‘yinchi"

    await message.reply_text(
        "🪙 PUL YUBORILDI!\n\n"
        f"👤 {sender_name} ➡️ {target_name}\n"
        f"🪙 Qabul qilindi: {amount:,} Pul\n"
        f"💸 Komissiya: {fee:,} Pul\n"
        f"🪙 Jami yechildi: {total:,} Pul"
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

def weapon_keyboard(user_id=None):
    buttons = []

    user = get_user(user_id) if user_id is not None else None
    inventory = user.get("inventory", {}) if user else {}

    owned = ["weapon_01"]

    for weapon_id in WEAPONS:
        if int(inventory.get(weapon_id, 0)) > 0 and weapon_id not in owned:
            owned.append(weapon_id)

    for weapon_id in owned:
        weapon = get_weapon(weapon_id)
        if not weapon:
            continue

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

    weapon_id = resolve_weapon_id(
        room.get("weapon", {}).get(user_id, "pistol")
    )
    weapon_name = WEAPONS[weapon_id]["name"]

    user = get_user(user_id)

    weapon_levels = user.get("weapon_levels", {})
    weapon_xp = user.get("weapon_xp", {})

    weapon_level = int(weapon_levels.get(weapon_id, 1))
    current_xp = int(weapon_xp.get(weapon_id, 0))

    try:
        # ⭐ Jang oynasi ham magazindagi shu qurolning XP sig'imini ko'rsatadi.
        weapon_shop_xp = int(WEAPONS[weapon_id].get("shop_xp", 100))
        xp_limit = int(
            xp_capacity(
                weapon_level,
                weapon_shop_xp,
            )
        )
    except Exception:
        xp_limit = 100

    medkits_left = max(
        0,
        3 - int(room["medkit_used"].get(user_id, 0))
    )

    return (
        f"{side_name}\n\n"
        f"❤️ HP: {room['hp'].get(user_id, 0)}/100\n"
        f"⚡ Energy: {room['energy'].get(user_id, 0)}/100\n"
        f"🔫 Qurol: {weapon_name}\n"
        f"⭐ Level: {weapon_level}/15\n"
        f"✨ XP: {current_xp}/{xp_limit}\n"
        f"🛡 Himoya: "
        f"{'Ishlatilgan' if room['defense_used'].get(user_id) else 'Mavjud'}\n"
        f"💊 Aptechka: {medkits_left} ta\n\n"
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

def finish_battle_rewards(chat_id, winner):
    room = GAME_ROOMS.get(chat_id)

    if not room:
        return {
            "pul": 0,
            "bonus": 0,
            "almas": 0,
            "players": 0,
        }

    # 🔒 Bir jang uchun mukofot faqat bir marta beriladi.
    if room.get("rewards_given"):
        return {
            "pul": 0,
            "bonus": 0,
            "almas": 0,
            "players": 0,
        }

    room["rewards_given"] = True

    data = load_data()

    settings = data.setdefault("settings", {})

    win_reward = int(settings.get("win_reward", 50))
    team_bonus = int(settings.get("team_bonus", 50))
    streak_target = int(settings.get("win_streak_for_almas", 10))

    win_reward = max(0, win_reward)
    team_bonus = max(0, team_bonus)
    streak_target = max(1, streak_target)

    winners = [
        uid for uid in room.get("players", [])
        if room.get("sides", {}).get(uid) == winner
    ]

    losers = [
        uid for uid in room.get("players", [])
        if room.get("sides", {}).get(uid) != winner
    ]

    almas_count = 0

    for user_id in winners:
        uid = str(user_id)

        user = data["users"].get(uid)
        if user is None:
            user = {
                "pul": 0,
                "almas": 0,
                "win_streak": 0,
                "wins": 0,
                "losses": 0,
            }

        user["pul"] = int(user.get("pul", 0)) + win_reward
        user["pul"] += team_bonus

        user["wins"] = int(user.get("wins", 0)) + 1
        user["battle_wins"] = int(user.get("battle_wins", 0)) + 1

        streak = int(user.get("win_streak", 0)) + 1

        if streak >= streak_target:
            user["almas"] = int(user.get("almas", 0)) + 1
            almas_count += 1
            streak = 0

        user["win_streak"] = streak

        # 🏅 Achievementlarni tekshirish
        new_achievements = check_achievements(user)

        data["users"][uid] = user

        # 🔟 10.3 — G‘alaba va mukofot statistikasi.
        try:
            from top_stats import top10_3_record_group_event

            _earned_pul = win_reward + team_bonus

            top10_3_record_group_event(
                data,
                chat_id,
                user_id,
                "wins",
                1,
            )

            top10_3_record_group_event(
                data,
                chat_id,
                user_id,
                "pul",
                _earned_pul,
            )

            if streak >= streak_target:
                top10_3_record_group_event(
                    data,
                    chat_id,
                    user_id,
                    "almas",
                    1,
                )

            user["pul_earned"] = (
                int(user.get("pul_earned", 0))
                + _earned_pul
            )

            if streak == 0:
                user["almas_earned"] = (
                    int(user.get("almas_earned", 0))
                    + 1
                )

            data["users"][uid] = user

            print(
                f"✅ 10.3 WIN/REWARD STAT: "
                f"user={user_id} "
                f"pul={_earned_pul}"
            )
        except Exception as e:
            print(
                f"❌ 10.3 WIN/REWARD STAT XATOSI: "
                f"user={user_id} chat={chat_id} error={e}"
            )

        # 🎁 Yangi Achievementlar room logiga yoziladi
        for achievement_id in new_achievements:
            room.setdefault("achievement_rewards", {}).setdefault(
                uid,
                []
            ).append(achievement_id)

    for user_id in losers:
        uid = str(user_id)

        user = data["users"].get(uid)
        if user is None:
            user = {
                "pul": 0,
                "almas": 0,
                "win_streak": 0,
                "wins": 0,
                "losses": 0,
            }

        user["losses"] = int(user.get("losses", 0)) + 1
        user["battle_losses"] = int(user.get("battle_losses", 0)) + 1
        user["win_streak"] = 0

        data["users"][uid] = user

        # 🔟 10.3 — Mag‘lubiyat statistikasi.
        try:
            from top_stats import top10_3_record_group_event

            top10_3_record_group_event(
                data,
                chat_id,
                user_id,
                "losses",
                1,
            )

            print(
                f"✅ 10.3 LOSS STAT: "
                f"user={user_id} chat={chat_id}"
            )
        except Exception as e:
            print(
                f"❌ 10.3 LOSS STAT XATOSI: "
                f"user={user_id} chat={chat_id} error={e}"
            )

    save_data(data)

    return {
        "pul": win_reward,
        "bonus": team_bonus,
        "almas": almas_count,
        "players": len(winners),
    }


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

    attacker_user = get_user(attacker_id)
    if not attacker_user:
        ensure_user(attacker_id)
        attacker_user = get_user(attacker_id)

    equipped_raw = attacker_user.get("equipped_weapon", "pistol")
    weapon_id = resolve_weapon_id(equipped_raw)
    weapon = get_weapon(weapon_id)

    if not weapon:
        weapon_id = "weapon_01"
        weapon = get_weapon(weapon_id)

    weapon_levels = attacker_user.setdefault("weapon_levels", {})
    weapon_xp = attacker_user.setdefault("weapon_xp", {})

    level = int(weapon_levels.get(weapon_id, 1))
    level = max(1, min(level, 15))

    xp = int(weapon_xp.get(weapon_id, 0))
    xp = max(0, xp)

    base_damage = int(weapon.get("damage", 0))
    damage = weapon_damage(base_damage, level)

    blocked = False

    if room["defense_used"].get(target_id):
        room["defense_used"][target_id] = False
        damage = 0
        blocked = True

    old_target_hp = int(room["hp"].get(target_id, 0))
    room["hp"][target_id] = max(0, old_target_hp - damage)

    actual_damage = old_target_hp - room["hp"][target_id]

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

    # Faqat haqiqiy zarar berilgan hujum qurolga XP beradi.
    new_xp = xp
    new_level = level

    if actual_damage > 0:
        # ⭐ Har qurol o'zining magazindagi shop_xp sig'imidan boshlaydi.
        weapon_shop_xp = int(weapon.get("shop_xp", 100))

        new_xp, new_level = add_weapon_xp(
            xp,
            level,
            10,
            weapon_shop_xp,
        )

    weapon_xp[weapon_id] = new_xp
    weapon_levels[weapon_id] = new_level

    attacker_user["equipped_weapon"] = weapon_id
    attacker_user["battle_damage"] = (
        int(attacker_user.get("battle_damage", 0))
        + actual_damage
    )

    data = load_data()
    data["users"][str(attacker_id)] = attacker_user

    target_user = data["users"].get(str(target_id))
    if target_user is None:
        ensure_user(target_id)
        data = load_data()
        target_user = data["users"].get(str(target_id), {})

    target_user["battle_damage_taken"] = (
        int(target_user.get("battle_damage_taken", 0))
        + actual_damage
    )

    data["users"][str(target_id)] = target_user
    save_data(data)

    room.setdefault("round_logs", []).append({
        "attacker_id": attacker_id,
        "attacker_name": attacker_name,
        "target_id": target_id,
        "target_name": target_name,
        "weapon_id": weapon_id,
        "weapon_name": weapon.get("name", weapon_id),
        "weapon_level": new_level,
        "damage": actual_damage,
        "target_hp": room["hp"][target_id],
        "blocked": blocked,
    })

    if blocked:
        return True, 0

    return True, actual_damage

async def battle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    user_id = query.from_user.id
    chat_id = context.user_data.get("battle_chat_id")

    # 📩 Private panel avtomatik yuborilganda user_data mavjud bo‘lmasligi mumkin.
    # Faqat shu holatda foydalanuvchi qatnashayotgan faol jangni topamiz.
    if chat_id is None:
        for active_chat_id, active_room in GAME_ROOMS.items():
            if (
                active_room.get("phase") == "battle"
                and user_id in active_room.get("players", [])
                and user_id in active_room.get("sides", {})
            ):
                chat_id = active_chat_id
                context.user_data["battle_chat_id"] = chat_id
                break

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

        # 🔟 10.3 — Hujum statistikasi.
        try:
            from top_stats import top10_3_record_group_event
            from database import load_data, save_data

            _top_data = load_data()

            top10_3_record_group_event(
                _top_data,
                chat_id,
                user_id,
                "attacks",
                1,
            )

            _attack_damage = max(0, int(result))

            if _attack_damage > 0:
                top10_3_record_group_event(
                    _top_data,
                    chat_id,
                    user_id,
                    "damage",
                    _attack_damage,
                )

            _target_hp_after = int(
                room["hp"].get(target_id, 0)
            )

            if (
                _attack_damage > 0
                and _target_hp_after <= 0
            ):
                top10_3_record_group_event(
                    _top_data,
                    chat_id,
                    user_id,
                    "kills",
                    1,
                )

            save_data(_top_data)

            print(
                f"✅ 10.3 ATTACK STAT: "
                f"attacker={user_id} "
                f"damage={_attack_damage} "
                f"target={target_id} "
                f"hp={_target_hp_after}"
            )
        except Exception as e:
            print(
                f"❌ 10.3 ATTACK STAT XATOSI: "
                f"chat={chat_id} error={e}"
            )

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

        # 👥 LIVE PLAYERS + HP REFRESH
        # Hujumdan keyingi haqiqiy HP holatini guruh paneliga chiqaramiz.
        # Mavjud hujum/reward/winner kodiga tegilmaydi.
        try:
            from game import (
                battle_live_players_text,
                battle_live_players_keyboard,
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text=battle_live_players_text(room),
                reply_markup=battle_live_players_keyboard(room),
            )

            print(
                f"✅ LIVE HP REFRESH: "
                f"attack={user_id} -> target={target_id} | "
                f"chat={chat_id}"
            )

        except Exception as e:
            print(
                f"❌ LIVE HP REFRESH XATOSI: "
                f"chat={chat_id} | error={e}"
            )

        winner = check_winner(chat_id)

        if winner:
            winner_name = (
                "🔵 KO‘K" if winner == "blue"
                else "🔴 QIZIL"
            )

            reward = finish_battle_rewards(chat_id, winner)

            # 📩 Har bir o‘yinchiga shaxsiy jang natijasi
            try:
                final_data = load_data()

                for player_id in room.get("players", []):
                    uid = str(player_id)
                    player_data = final_data.get("users", {}).get(uid, {})

                    is_winner = (
                        room.get("sides", {}).get(player_id) == winner
                    )

                    player_side = room.get("sides", {}).get(player_id)

                    if player_side == "blue":
                        player_side_name = "🔵 KO‘KLAR"
                    else:
                        player_side_name = "🔴 QIZILLAR"

                    winner_side_name = (
                        "🔵 KO‘KLAR"
                        if winner == "blue"
                        else "🔴 QIZILLAR"
                    )

                    damage = int(
                        room.get("battle_damage", {}).get(player_id, 0)
                    )

                    if is_winner:
                        personal_pul = reward["pul"]
                        team_bonus = reward["bonus"]

                        # 🎁 Almas aynan shu o‘yinchiga berilganmi?
                        old_almas = int(
                            room.get("almas_before_reward", {}).get(
                                player_id,
                                player_data.get("almas", 0)
                            )
                        )
                        current_almas = int(
                            player_data.get("almas", 0)
                        )
                        personal_almas = max(
                            0,
                            current_almas - old_almas
                        )

                        streak = int(
                            player_data.get("win_streak", 0)
                        )

                        result_text = (
                            "🏆━━━━━━━━━━━━━━━━━━🏆\n"
                            "       ⚔️ JANG TUGADI\n"
                            "🏆━━━━━━━━━━━━━━━━━━🏆\n\n"
                            f"{winner_side_name} G‘OLIB!\n\n"
                            "🎯 SIZNING NATIJANGIZ\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            f"💥 Zarar: {damage}\n"
                            "🏆 G‘alaba: +1\n"
                            f"🔥 Win streak: {streak}\n"
                            "━━━━━━━━━━━━━━━━━━\n\n"
                            "💰 SIZGA BERILDI\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            f"💵 Jang mukofoti: +{personal_pul} Pul\n"
                            f"🎁 Jamoa bonusi: +{team_bonus} Pul\n"
                            f"💰 Jami: +{personal_pul + team_bonus} Pul\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            f"💎 Almas: +{personal_almas}\n\n"
                            "✨ Tabriklaymiz! Zo‘r jang!"
                        )
                    else:
                        streak = int(
                            player_data.get("win_streak", 0)
                        )

                        result_text = (
                            "⚔️━━━━━━━━━━━━━━━━━━⚔️\n"
                            "       ⚔️ JANG TUGADI\n"
                            "⚔️━━━━━━━━━━━━━━━━━━⚔️\n\n"
                            f"{winner_side_name} G‘OLIB!\n\n"
                            "📊 SIZNING NATIJANGIZ\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            f"👥 Jamoa: {player_side_name}\n"
                            f"💥 Zarar: {damage}\n"
                            "💀 Mag‘lubiyat: +1\n"
                            f"🔥 Win streak: {streak}\n"
                            "━━━━━━━━━━━━━━━━━━\n\n"
                            "💰 MUKOFOT\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            "💵 Jang mukofoti: +0 Pul\n"
                            "🎁 Jamoa bonusi: +0 Pul\n"
                            "💎 Almas: +0\n"
                            "━━━━━━━━━━━━━━━━━━\n\n"
                            "🎯 Keyingi jangda omad!"
                        )

                    await context.bot.send_message(
                        chat_id=player_id,
                        text=result_text
                    )

            except Exception as e:
                print(
                    f"⚠️ PRIVATE BATTLE RESULT XATOSI: "
                    f"chat={chat_id} | error={e}"
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
                        f"💥 Zarar: {result}\n\n"
                        f"💰 Har bir g‘olib: +{reward['pul']} Pul\n"
                        f"🎁 Jamoa bonusi: +{reward['bonus']} Pul"
                        + (
                            f"\n💎 Almas: +{reward['almas']}"
                            if reward["almas"] > 0
                            else ""
                        )
                    )
                )
            except Exception:
                pass

            await query.edit_message_text(
                f"🏆 {winner_name} G‘OLIB!\n\n"
                f"💥 Yetkazilgan zarar: {result}\n"
                f"❤️ {target_name}: 0 HP\n\n"
                f"💰 Mukofot: +{reward['pul']} Pul\n"
                f"🎁 Jamoa bonusi: +{reward['bonus']} Pul"
                + (
                    f"\n💎 Almas: +{reward['almas']}"
                    if reward["almas"] > 0
                    else ""
                )
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

        user = get_user(user_id)

        if not user:
            ensure_user(user_id)
            user = get_user(user_id)

        inventory = user.get("inventory", {})
        if not isinstance(inventory, dict):
            inventory = {}

        shop = load_shop()
        defense_items = (
            shop.get("categories", {})
            .get("defense", {})
            .get("items", {})
        )

        buttons = []

        for item_id, item in defense_items.items():
            count = int(inventory.get(item_id, 0))

            if count <= 0:
                continue

            defense_hp = 0

            for effect in item.get("effects", []):
                if effect.get("effect_type") == "defense_hp":
                    defense_hp = int(effect.get("value", 0))
                    break

            if defense_hp <= 0:
                continue

            buttons.append([
                InlineKeyboardButton(
                    f"{item.get('name', item_id)} ×{count} 🛡️+{defense_hp}",
                    callback_data=f"battle_defense_use:{item_id}"
                )
            ])

        if not buttons:
            await query.answer(
                "🛡️ Inventarda himoya buyumi yo‘q.",
                show_alert=True
            )
            return

        buttons.append([
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="battle_menu"
            )
        ])

        await query.edit_message_text(
            "🛡️ HIMOYA\n\n"
            "Himoya buyumini tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # HIMOYA ISHLATISH
    if data.startswith("battle_defense_use:"):
        item_id = data.split(":", 1)[1]

        if room["defense_used"].get(user_id):
            await query.answer(
                "🛡 Himoyani allaqachon ishlatgansiz.",
                show_alert=True
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
                "❌ Bu himoya buyumi inventarda yo‘q.",
                show_alert=True
            )
            return

        shop = load_shop()
        item = (
            shop.get("categories", {})
            .get("defense", {})
            .get("items", {})
            .get(item_id)
        )

        if not item:
            await query.answer(
                "❌ Himoya buyumi topilmadi.",
                show_alert=True
            )
            return

        defense_hp = 0

        for effect in item.get("effects", []):
            if effect.get("effect_type") == "defense_hp":
                defense_hp = int(effect.get("value", 0))
                break

        if defense_hp <= 0:
            await query.answer(
                "❌ Bu himoya buyumida himoya effekti yo‘q.",
                show_alert=True
            )
            return

        # Battle'dagi bir martalik blok uchun buyum ishlatiladi.
        room["defense_used"][user_id] = True
        room.setdefault("defense_item", {})
        room["defense_item"][user_id] = {
            "item_id": item_id,
            "defense_hp": defense_hp,
        }

        inventory[item_id] = count - 1

        if inventory[item_id] <= 0:
            inventory.pop(item_id, None)

        user["inventory"] = inventory
        user["defense_hp"] = int(user.get("defense_hp", 0)) + defense_hp
        data_all = load_data()
        data_all["users"][str(user_id)] = user

        # 🔟 10.3 — Himoya ishlatilganini statistikaga yozish.
        try:
            from top_stats import top10_3_record_group_event

            top10_3_record_group_event(
                data_all,
                chat_id,
                user_id,
                "defenses",
                1,
            )

            print(
                f"✅ 10.3 DEFENSE STAT: "
                f"user={user_id} chat={chat_id}"
            )
        except Exception as e:
            print(
                f"❌ 10.3 DEFENSE STAT XATOSI: "
                f"chat={chat_id} error={e}"
            )

        save_data(data_all)

        await query.answer(
            f"🛡️ Himoya yoqildi: +{defense_hp}",
            show_alert=True
        )

        await query.edit_message_text(
            f"🛡️ {item.get('name', item_id)} ishlatildi!\n\n"
            f"🛡️ Himoya: +{defense_hp}\n"
            "⚔️ Keyingi keladigan zarba bloklanadi.\n\n"
            + battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

    # APTECHKA
    if data == "battle_medkit":
        medkits_used = int(
            room.get("medkit_used", {}).get(user_id, 0)
        )

        if medkits_used >= 3:
            await query.answer(
                "🩹 Bu jangda 3 ta aptechka ishlatib bo‘lgansiz.",
                show_alert=True
            )
            return

        user = get_user(user_id)

        if not user:
            ensure_user(user_id)
            user = get_user(user_id)

        inventory = user.get("inventory", {})
        if not isinstance(inventory, dict):
            inventory = {}

        shop = load_shop()
        medkit_items = (
            shop.get("categories", {})
            .get("medkits", {})
            .get("items", {})
        )

        buttons = []

        for item_id, item in medkit_items.items():
            count = int(inventory.get(item_id, 0))

            if count <= 0:
                continue

            heal = 0

            for effect in item.get("effects", []):
                if effect.get("effect_type") == "hp":
                    heal = int(effect.get("value", 0))
                    break

            if heal <= 0:
                continue

            buttons.append([
                InlineKeyboardButton(
                    f"{item.get('name', item_id)} ×{count} ❤️+{heal}",
                    callback_data=f"battle_medkit_use:{item_id}"
                )
            ])

        if not buttons:
            await query.answer(
                "🩹 Inventarda medkit yo‘q.",
                show_alert=True
            )
            return

        buttons.append([
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="battle_menu"
            )
        ])

        await query.edit_message_text(
            "🩹 APTECHKA\n\n"
            "Davolash uchun buyumni tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # APTECHKA ISHLATISH
    if data.startswith("battle_medkit_use:"):
        item_id = data.split(":", 1)[1]

        medkits_used = int(
            room.get("medkit_used", {}).get(user_id, 0)
        )

        if medkits_used >= 3:
            await query.answer(
                "🩹 Bu jangda 3 ta aptechka ishlatib bo‘lgansiz.",
                show_alert=True
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
                "❌ Bu medkit inventarda yo‘q.",
                show_alert=True
            )
            return

        hp = int(room["hp"].get(user_id, 0))

        if hp >= 100:
            await query.answer(
                "❤️ HP allaqachon 100.",
                show_alert=True
            )
            return

        shop = load_shop()
        item = (
            shop.get("categories", {})
            .get("medkits", {})
            .get("items", {})
            .get(item_id)
        )

        if not item:
            await query.answer(
                "❌ Medkit topilmadi.",
                show_alert=True
            )
            return

        heal = 0

        for effect in item.get("effects", []):
            if effect.get("effect_type") == "hp":
                heal = int(effect.get("value", 0))
                break

        if heal <= 0:
            await query.answer(
                "❌ Bu medkitda HP effekti yo‘q.",
                show_alert=True
            )
            return

        old_hp = hp
        room["hp"][user_id] = min(100, hp + heal)
        actual_heal = room["hp"][user_id] - old_hp

        inventory[item_id] = count - 1

        if inventory[item_id] <= 0:
            inventory.pop(item_id, None)

        user["inventory"] = inventory

        room.setdefault("medkit_used", {})
        room["medkit_used"][user_id] = medkits_used + 1
        remaining_medkits = 3 - room["medkit_used"][user_id]

        data_all = load_data()
        data_all["users"][str(user_id)] = user
        # 🔟 10.3 — Aptechka ishlatilganini statistikaga yozish.
        try:
            from top_stats import top10_3_record_group_event

            top10_3_record_group_event(
                data_all,
                chat_id,
                user_id,
                "medkits",
                1,
            )

            print(
                f"✅ 10.3 MEDKIT STAT: "
                f"user={user_id} chat={chat_id}"
            )
        except Exception as e:
            print(
                f"❌ 10.3 MEDKIT STAT XATOSI: "
                f"chat={chat_id} error={e}"
            )

        save_data(data_all)

        await query.answer(
            f"🩹 +{actual_heal} HP | Qoldi: {remaining_medkits}/3",
            show_alert=True
        )

        await query.edit_message_text(
            f"🩹 {item.get('name', item_id)} ishlatildi!\n\n"
            f"❤️ +{actual_heal} HP\n"
            f"❤️ HP: {room['hp'][user_id]}/100\n"f"🩹 Qoldi: {remaining_medkits}/3\n\n"
            + battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

    # QUROL TANLASH
    if data == "battle_weapon":
        await query.edit_message_text(
            "🔫 Qurolni tanlang:",
            reply_markup=weapon_keyboard(user_id)
        )
        return

    # QUROLNI O‘ZGARTIRISH
    if data.startswith("weapon:"):
        weapon_id = data.split(":", 1)[1]

        if weapon_id not in WEAPONS:
            await query.answer(
                "❌ Qurol topilmadi.",
                show_alert=True
            )
            return

        user = get_user(user_id)
        if not user:
            ensure_user(user_id)
            user = get_user(user_id)

        inventory = user.get("inventory", {})
        if not isinstance(inventory, dict):
            inventory = {}

        # 🔫 Boshlang‘ich pistol doim mavjud.
        # Boshqa qurollar inventarda bo‘lishi shart.
        if (
            weapon_id != "weapon_01"
            and int(inventory.get(weapon_id, 0)) <= 0
        ):
            await query.answer(
                "❌ Bu qurol inventaringizda yo‘q.",
                show_alert=True
            )
            return

        if "weapon" not in room:
            room["weapon"] = {}

        room["weapon"][user_id] = weapon_id

        # 🔫 Tanlangan qurolni foydalanuvchi profiliga doimiy saqlash
        user["equipped_weapon"] = weapon_id

        # 💾 Database'ga yozish
        db_data = load_data()
        db_data["users"][str(user_id)] = user
        save_data(db_data)

        await query.edit_message_text(
            f"🔫 Tanlangan qurol:\n"
            f"{WEAPONS[weapon_id]['name']}\n\n"
            + battle_text(room, user_id),
            reply_markup=battle_keyboard()
        )
        return

if __name__ == "__main__":
    main()
