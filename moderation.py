import re
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ChatPermissions,
)
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone

from database import load_data, save_data, is_admin


MOD_PAGE_1 = [
    ("📜 Qoidalar", "rules"),
    ("🛡️ Anti-Spam", "antispam"),
    ("👋 Salomlashish", "welcome"),
    ("🌊 Anti-Flood", "antiflood"),
    ("👋 Xayrlashuv", "goodbye"),
    ("🔗 Anti-Link", "antilink"),
    ("📢 Anti-Reklama", "antireklama"),
    ("🔁 Anti-Repeat", "antirepeat"),
    ("🔠 Anti-Caps", "anticaps"),
    ("👥 Anti-Mention", "antimention"),
    ("📨 Anti-Forward", "antiforward"),
    ("🤖 Anti-Bot", "antibot"),
    ("🚫 Blok", "blacklist"),
    ("🖼️ Media", "media"),
    ("🔞 Porno", "porno"),
    ("⚠️ Ogohlantirish", "warn"),
    ("🔇 Mute", "mute"),
    ("🚫 Ban", "ban"),
    ("👢 Kick", "kick"),
    ("👑 Adminlar", "admins"),
    ("🗑️ Xabarlar", "messages"),
    ("📌 Pin", "pin"),
    ("🔒 Lock", "lock"),
    ("🔓 Unlock", "unlock"),
    ("🐢 Slowmode", "slowmode"),
    ("🛡️ Himoya", "protection"),
    ("🚨 Raid", "raid"),
    ("🆘 Emergency", "emergency"),
    ("👥 A’zolar", "members"),
    ("📊 Statistika", "stats"),
    ("📜 Loglar", "logs"),
    ("🔎 User Info", "userinfo"),
    ("📜 Tarix", "history"),
    ("🎉 Welcome", "welcome"),
    ("🚪 Goodbye", "goodbye"),
]


MOD_PAGE_2 = [
    ("📌 Mavzu", "topic"),
    ("🚫 Taqiqlangan so‘zlar", "blacklist_words"),
    ("🔁 Takroriy xabarlar", "repeat"),
    ("👥 A’zolar boshqaruvi", "member_manage"),
    ("🎭 Niqobli a’zo", "masked_member"),
    ("💬 Muhokama guruhi", "discussion"),
    ("🆕 Shaxsiy buyruqlar", "private_commands"),
    ("✨ Stikerlar va GIFlar", "stickers_gifs"),
    ("📏 Xabarlar uzunligi", "message_length"),
    ("📢 Kanallar boshqaruvi", "channels"),
    ("✅ Ruxsatnomalar", "permissions"),
    ("🆕 Kanal ulash", "channel_link"),
    ("⭐ VIP", "vip"),
    ("🛡️ Trusted", "trusted"),
    ("✅ Whitelist", "whitelist"),
    ("🚫 Blacklist", "blacklist"),
    ("⚙️ Avto-jazo", "auto_punishment"),
    ("🔄 Auto Restore", "auto_restore"),
    ("🧹 Auto Cleanup", "auto_cleanup"),
    ("🗑️ Service Messages", "service_messages"),
    ("🌙 Tun", "night_mode"),
    ("🏷️ Belgilash", "tagging"),
    ("💬 Xabar sozlamalari", "message_settings"),
    ("📈 Activity", "activity"),
    ("🏆 Faol a’zolar", "active_members"),
    ("⚠️ Warn statistikasi", "warn_stats"),
    ("🔇 Mute statistikasi", "mute_stats"),
    ("🚫 Ban statistikasi", "ban_stats"),
    ("🤖 Spam statistikasi", "spam_stats"),
    ("🚨 Raid statistikasi", "raid_stats"),
    ("🌐 Lang", "language"),
    ("⚙️ Boshqalar", "other"),
]


def _rows(items, prefix="modmenu"):
    rows = []
    for i in range(0, len(items), 2):
        row = [
            InlineKeyboardButton(
                items[i][0],
                callback_data=f"{prefix}:{items[i][1]}",
            )
        ]
        if i + 1 < len(items):
            row.append(
                InlineKeyboardButton(
                    items[i + 1][0],
                    callback_data=f"{prefix}:{items[i + 1][1]}",
                )
            )
        rows.append(row)
    return rows


def moderation_keyboard(page=1):
    items = MOD_PAGE_1 if page == 1 else MOD_PAGE_2
    rows = _rows(items)

    if page == 1:
        rows.append([
            InlineKeyboardButton("➡️ 2-SAHIFA", callback_data="modpage:2")
        ])
    else:
        rows.append([
            InlineKeyboardButton("⬅️ 1-SAHIFA", callback_data="modpage:1")
        ])

    rows.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="modback"),
        InlineKeyboardButton("❌ Yopish", callback_data="modclose"),
    ])

    return InlineKeyboardMarkup(rows)


def moderation_text(chat_title, page=1):
    page_text = "1/2" if page == 1 else "2/2"
    return (
        "🛡️ <b>GURUH MODERATSIYASI</b>\n\n"
        f"👥 <b>Guruh:</b> {chat_title}\n"
        f"📄 <b>Sahifa:</b> {page_text}\n\n"
        "Kerakli sozlamani tanlang:"
    )



# ============================================================
# 🌊 ANTI-FLOOD TIZIMI
# ============================================================

ANTIFLOOD_RUNTIME = {}

def _antiflood_config(mod):
    cfg = mod.setdefault("antiflood", {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("limit", 5)
    cfg.setdefault("window", 3)
    return cfg


def _antiflood_keyboard(cfg):
    enabled = bool(cfg.get("enabled", False))
    status = "✅ Yoqilgan" if enabled else "❌ O‘chirilgan"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                status,
                callback_data="modmenu:antiflood:toggle",
            )
        ],
        [
            InlineKeyboardButton(
                f"🔢 Limit: {cfg.get('limit', 5)}",
                callback_data="modmenu:antiflood:limit_menu",
            )
        ],
        [
            InlineKeyboardButton(
                f"⏱️ Oyna: {cfg.get('window', 3)}s",
                callback_data="modmenu:antiflood:window_menu",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Ortga",
                callback_data="modpage:1",
            )
        ],
    ])


def _antiflood_limit_keyboard():
    values = [3, 5, 10, 15, 20, 30, 50]
    rows = []

    for i in range(0, len(values), 3):
        rows.append([
            InlineKeyboardButton(
                f"🔢 {value}",
                callback_data=f"modmenu:antiflood:setlimit:{value}",
            )
            for value in values[i:i + 3]
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Anti-Flood",
            callback_data="modmenu:antiflood:back",
        )
    ])

    return InlineKeyboardMarkup(rows)


def _antiflood_window_keyboard():
    values = [2, 3, 5, 10, 15, 30, 60]
    rows = []

    for i in range(0, len(values), 3):
        rows.append([
            InlineKeyboardButton(
                f"⏱️ {value}s",
                callback_data=f"modmenu:antiflood:setwindow:{value}",
            )
            for value in values[i:i + 3]
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Anti-Flood",
            callback_data="modmenu:antiflood:back",
        )
    ])

    return InlineKeyboardMarkup(rows)


def _antiflood_text(cfg):
    enabled = bool(cfg.get("enabled", False))
    status = "✅ Yoqilgan" if enabled else "❌ O‘chirilgan"

    return (
        "🌊 <b>ANTI-FLOOD</b>\n\n"
        f"📌 Holat: <b>{status}</b>\n"
        f"🔢 Limit: <b>{cfg.get('limit', 5)} ta xabar</b>\n"
        f"⏱️ Oyna: <b>{cfg.get('window', 3)} soniya</b>\n\n"
        "ℹ️ Belgilangan vaqt ichida limitdan ortiq xabar yuborilsa, "
        "ortiqcha xabar avtomatik o‘chiriladi."
    )


def _antiflood_limit_text(cfg):
    return (
        "🔢 <b>ANTI-FLOOD — LIMIT</b>\n\n"
        f"📌 Hozirgi limit: <b>{cfg.get('limit', 5)} ta xabar</b>\n\n"
        "Nechta xabardan keyin flood hisoblanishini tanlang:"
    )


def _antiflood_window_text(cfg):
    return (
        "⏱️ <b>ANTI-FLOOD — VAQT OYNASI</b>\n\n"
        f"📌 Hozirgi oyna: <b>{cfg.get('window', 3)} soniya</b>\n\n"
        "Flood tekshiriladigan vaqtni tanlang:"
    )

async def settinghelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text(
            "🛡️ Bu buyruqni guruh ichida ishlating."
        )
        return

    await message.reply_text(
        "⚙️ <b>SOZLAMALAR MENYUSINI QAYERDA OCHMOQCHISIZ?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🏠 Shu yerda ochish",
                    callback_data="modopen:group",
                ),
                InlineKeyboardButton(
                    "💬 Shaxsiy Chatda Ochish",
                    callback_data="modopen:private",
                ),
            ]
        ]),
    )


async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data or ""
    user = query.from_user

    # 🔁 Anti-Repeat callback
    if data.startswith("modmenu:antirepeat"):
        await antirepeat_callback(update, context)
        return

    # 🔠 Anti-Caps callback
    if data.startswith("modmenu:anticaps"):
        await anticaps_callback(update, context)
        return

    # 👥 Anti-Mention callback
    if data.startswith("modmenu:antimention"):
        await antimention_callback(update, context)
        return

    if data == "modclose":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data.startswith("modpage:"):
        page = int(data.split(":", 1)[1])
        chat_title = "Guruh"

        if query.message and query.message.chat.type in ("group", "supergroup"):
            chat_title = query.message.chat.title or "Guruh"

        await query.edit_message_text(
            moderation_text(chat_title, page),
            parse_mode="HTML",
            reply_markup=moderation_keyboard(page),
        )
        return

    if data == "modopen:group":
        chat_title = query.message.chat.title or "Guruh"
        await query.edit_message_text(
            moderation_text(chat_title, 1),
            parse_mode="HTML",
            reply_markup=moderation_keyboard(1),
        )
        return

    if data == "modopen:private":
        chat = query.message.chat
        if chat.type not in ("group", "supergroup"):
            return

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=moderation_text(chat.title or "Guruh", 1),
                parse_mode="HTML",
                reply_markup=moderation_keyboard(1),
            )
            await query.edit_message_text(
                "📨 <b>Sozlamalar menyusi shaxsiy suhbatga yuborildi.</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "💬 Chatga o‘tish",
                            url="tg://user?id=" + str(user.id),
                        )
                    ]
                ]),
            )
        except Exception:
            await query.answer(
                "❌ Avval botga shaxsiy chatda /start yuboring.",
                show_alert=True,
            )
        return

    if data == "modback":
        await query.edit_message_text(
            "⚙️ <b>SOZLAMALAR MENYUSINI QAYERDA OCHMOQCHISIZ?</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🏠 Shu yerda ochish",
                        callback_data="modopen:group",
                    ),
                    InlineKeyboardButton(
                        "💬 Shaxsiy Chatda Ochish",
                        callback_data="modopen:private",
                    ),
                ]
            ]),
        )
        return

    if data.startswith("modmenu:antiflood:"):
        chat = query.message.chat if query.message else None

        if not chat or chat.type not in ("group", "supergroup"):
            await query.answer(
                "❌ Bu sozlama faqat guruh uchun.",
                show_alert=True,
            )
            return

        if not await _is_group_admin(update, context, user.id):
            await query.answer(
                "🚫 Sizda moderatsiya huquqi yo‘q.",
                show_alert=True,
            )
            return

        data_store = load_data()
        group, mod = _get_moderation_group(data_store, chat.id)
        cfg = _antiflood_config(mod)

        action = data.split(":")

        if len(action) < 3:
            return

        action_name = action[2]

        # ✅ / ❌ Yoqish-o‘chirish
        if action_name == "toggle":
            cfg["enabled"] = not bool(cfg.get("enabled", False))
            save_data(data_store)

            await query.edit_message_text(
                _antiflood_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_keyboard(cfg),
            )
            return

        # 🔢 Limit tanlash
        if action_name == "limit_menu":
            await query.edit_message_text(
                _antiflood_limit_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_limit_keyboard(),
            )
            return

        # ⏱️ Oyna tanlash
        if action_name == "window_menu":
            await query.edit_message_text(
                _antiflood_window_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_window_keyboard(),
            )
            return

        # 🔙 Anti-Flood oynasiga qaytish
        if action_name == "back":
            await query.edit_message_text(
                _antiflood_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_keyboard(cfg),
            )
            return

        # 🔢 Limitni saqlash
        if action_name == "setlimit" and len(action) == 4:
            try:
                value = int(action[3])
            except ValueError:
                await query.answer("❌ Noto‘g‘ri limit.", show_alert=True)
                return

            if value not in (3, 5, 10, 15, 20, 30, 50):
                await query.answer("❌ Bu limit mavjud emas.", show_alert=True)
                return

            cfg["limit"] = value
            save_data(data_store)

            await query.edit_message_text(
                _antiflood_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_keyboard(cfg),
            )
            return

        # ⏱️ Vaqtni saqlash
        if action_name == "setwindow" and len(action) == 4:
            try:
                value = int(action[3])
            except ValueError:
                await query.answer("❌ Noto‘g‘ri vaqt.", show_alert=True)
                return

            if value not in (2, 3, 5, 10, 15, 30, 60):
                await query.answer("❌ Bu vaqt mavjud emas.", show_alert=True)
                return

            cfg["window"] = value
            save_data(data_store)

            await query.edit_message_text(
                _antiflood_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_keyboard(cfg),
            )
            return

        return

    if data == "modmenu:antilink" or data.startswith("modmenu:antilink:"):
        data_store = load_data()

        source_chat_id = query.message.chat.id if query.message else None
        if not source_chat_id:
            return

        group, mod = _get_moderation_group(data_store, source_chat_id)

        # Faqat guruh administratori yoki bot administratori
        if not await _is_group_admin(update, context, query.from_user.id):
            await query.answer("❌ Faqat guruh administratori sozlay oladi.", show_alert=True)
            return

        cfg = _antilink_config(mod)

        if data == "modmenu:antilink:toggle":
            cfg["enabled"] = not bool(cfg.get("enabled", False))
            save_data(data_store)

        elif data == "modmenu:antilink:delete":
            cfg["delete"] = not bool(cfg.get("delete", True))
            save_data(data_store)

        elif data == "modmenu:antilink:actions":
            await query.edit_message_text(
                "⚙️ <b>Anti-Link jazosi</b>\n\n"
                "Qaysi jazo ishlatilishini tanlang:",
                parse_mode="HTML",
                reply_markup=_antilink_actions_keyboard(),
            )
            return

        elif data.startswith("modmenu:antilink:setaction:"):
            action = data.rsplit(":", 1)[1]
            if action not in ("warn", "mute", "ban"):
                await query.answer("❌ Noto‘g‘ri jazo.", show_alert=True)
                return

            cfg["action"] = action
            save_data(data_store)

        elif data == "modmenu:antilink:duration":
            await query.edit_message_text(
                "⏱️ <b>Mute muddati</b>\n\n"
                "Kerakli muddatni tanlang:",
                parse_mode="HTML",
                reply_markup=_antilink_duration_keyboard(),
            )
            return

        elif data.startswith("modmenu:antilink:setduration:"):
            duration_value = data.rsplit(":", 1)[1]

            if duration_value not in (
                "1m", "5m", "10m", "30m",
                "1h", "6h", "12h", "1d", "7d",
                "permanent",
            ):
                await query.answer("❌ Noto‘g‘ri muddat.", show_alert=True)
                return

            cfg["mute_duration"] = duration_value
            save_data(data_store)

        elif data == "modmenu:antilink:back":
            await query.edit_message_text(
                _antilink_text(cfg),
                parse_mode="HTML",
                reply_markup=_antilink_keyboard(cfg),
            )
            return

        await query.edit_message_text(
            _antilink_text(cfg),
            parse_mode="HTML",
            reply_markup=_antilink_keyboard(cfg),
        )
        return

    if data == "modmenu:antireklama" or data.startswith("modmenu:antireklama:"):
        data_store = load_data()
        source_chat_id = query.message.chat.id if query.message else None
        if not source_chat_id:
            await query.answer("❌ Guruh aniqlanmadi.", show_alert=True)
            return

        source_group = data_store.setdefault("groups", {}).setdefault(
            str(source_chat_id),
            {
                "chat_id": source_chat_id,
                "title": query.message.chat.title if query.message.chat else "Noma'lum guruh",
                "first_seen": None,
                "last_seen": None,
                "battles": 0,
                "players": {},
                "damage": 0,
                "wins": 0,
                "defenses": 0,
                "medkits": 0,
                "moderation": {},
            },
        )
        source_group.setdefault("moderation", {})
        mod = source_group["moderation"]
        cfg = _antireklama_config(mod)

        if not await _is_group_admin(update, context, query.from_user.id):
            await query.answer("⛔ Faqat guruh adminlari.", show_alert=True)
            return

        action = data.split(":")[2] if len(data.split(":")) >= 3 else ""

        if action == "toggle":
            cfg["enabled"] = not bool(cfg.get("enabled", False))
            save_data(data_store)

        elif action == "delete":
            cfg["delete"] = not bool(cfg.get("delete", True))
            save_data(data_store)

        elif action == "actions":
            await query.answer()
            await query.edit_message_text(
                _antireklama_text(cfg, source_group.get("title", "Guruh")),
                reply_markup=_antireklama_actions_keyboard(cfg),
            )
            return

        elif action == "setaction":
            value = data.split(":")[3] if len(data.split(":")) >= 4 else ""
            if value in ("warn", "mute", "ban"):
                cfg["action"] = value
                save_data(data_store)

        elif action == "duration":
            await query.answer()
            await query.edit_message_text(
                _antireklama_text(cfg, source_group.get("title", "Guruh")),
                reply_markup=_antireklama_duration_keyboard(cfg),
            )
            return

        elif action == "setduration":
            value = data.split(":")[3] if len(data.split(":")) >= 4 else ""
            allowed = {
                "60": "1 daqiqa",
                "300": "5 daqiqa",
                "600": "10 daqiqa",
                "1800": "30 daqiqa",
                "3600": "1 soat",
                "21600": "6 soat",
                "43200": "12 soat",
                "86400": "1 kun",
                "604800": "7 kun",
                "permanent": "♾️ Doimiy",
            }
            if value in allowed:
                cfg["mute_duration"] = value
                save_data(data_store)

        elif action == "back":
            await query.answer()
            await query.edit_message_text(
                _antireklama_text(cfg, source_group.get("title", "Guruh")),
                reply_markup=_antireklama_keyboard(cfg),
            )
            return

        await query.answer()
        await query.edit_message_text(
            _antireklama_text(cfg, source_group.get("title", "Guruh")),
            reply_markup=_antireklama_keyboard(cfg),
        )
        return

    if data.startswith("modmenu:"):
        section = data.split(":", 1)[1]

        names = {
            "rules": "📜 Qoidalar",
            "antispam": "🛡️ Anti-Spam",
            "welcome": "👋 Salomlashish",
            "antiflood": "🌊 Anti-Flood",
            "goodbye": "👋 Xayrlashuv",
            "antilink": "🔗 Anti-Link",
            "antireklama": "📢 Anti-Reklama",
            "antirepeat": "🔁 Anti-Repeat",
            "anticaps": "🔠 Anti-Caps",
            "antimention": "👥 Anti-Mention",
            "antiforward": "📨 Anti-Forward",
            "antibot": "🤖 Anti-Bot",
            "blacklist": "🚫 Blacklist",
            "media": "🖼️ Media",
            "porno": "🔞 Porno",
            "warn": "⚠️ Ogohlantirish",
            "mute": "🔇 Mute",
            "ban": "🚫 Ban",
            "kick": "👢 Kick",
            "admins": "👑 Adminlar",
            "messages": "🗑️ Xabarlar",
            "pin": "📌 Pin",
            "lock": "🔒 Lock",
            "unlock": "🔓 Unlock",
            "slowmode": "🐢 Slowmode",
            "protection": "🛡️ Himoya",
            "raid": "🚨 Raid",
            "emergency": "🆘 Emergency",
            "members": "👥 A’zolar",
            "stats": "📊 Statistika",
            "logs": "📜 Loglar",
            "userinfo": "🔎 User Info",
            "history": "📜 Tarix",
            "topic": "📌 Mavzu",
            "blacklist_words": "🚫 Taqiqlangan so‘zlar",
            "repeat": "🔁 Takroriy xabarlar",
            "member_manage": "👥 A’zolar boshqaruvi",
            "masked_member": "🎭 Niqobli a’zo",
            "discussion": "💬 Muhokama guruhi",
            "private_commands": "🆕 Shaxsiy buyruqlar",
            "stickers_gifs": "✨ Stikerlar va GIFlar",
            "message_length": "📏 Xabarlar uzunligi",
            "channels": "📢 Kanallar boshqaruvi",
            "permissions": "✅ Ruxsatnomalar",
            "channel_link": "🆕 Kanal ulash",
            "vip": "⭐ VIP",
            "trusted": "🛡️ Trusted",
            "whitelist": "✅ Whitelist",
            "auto_punishment": "⚙️ Avto-jazo",
            "auto_restore": "🔄 Auto Restore",
            "auto_cleanup": "🧹 Auto Cleanup",
            "service_messages": "🗑️ Service Messages",
            "night_mode": "🌙 Tun",
            "tagging": "🏷️ Belgilash",
            "message_settings": "💬 Xabar sozlamalari",
            "activity": "📈 Activity",
            "active_members": "🏆 Faol a’zolar",
            "warn_stats": "⚠️ Warn statistikasi",
            "mute_stats": "🔇 Mute statistikasi",
            "ban_stats": "🚫 Ban statistikasi",
            "spam_stats": "🤖 Spam statistikasi",
            "raid_stats": "🚨 Raid statistikasi",
            "language": "🌐 Lang",
            "other": "⚙️ Boshqalar",
        }

        if section == "antiflood":
            data_store = load_data()
            group, mod = _get_moderation_group(data_store, query.message.chat.id)
            cfg = _antiflood_config(mod)

            await query.edit_message_text(
                _antiflood_text(cfg),
                parse_mode="HTML",
                reply_markup=_antiflood_keyboard(cfg),
            )
            return

        title = names.get(section, "⚙️ Sozlama")
        await query.answer(f"{title} keyingi bosqichda ulanadi.", show_alert=True)


# ============================================================
# ⚠️ WARN TIZIMI — 2-QADAM
# ============================================================



# ============================================================
# 🔗 ANTI-LINK — GURUH MODERATSIYASI
# ============================================================

def _antilink_config(mod):
    cfg = mod.setdefault("antilink", {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("delete", True)
    cfg.setdefault("action", "warn")
    cfg.setdefault("mute_duration", "1h")
    cfg.setdefault("violations", {})
    cfg.setdefault("warns", {})
    return cfg


def _antilink_action_name(action):
    return {
        "warn": "⚠️ Warn",
        "mute": "🔇 Mute",
        "ban": "🚫 Ban",
    }.get(action, "⚠️ Warn")


def _antilink_duration_name(value):
    return {
        "1m": "1 daqiqa",
        "5m": "5 daqiqa",
        "10m": "10 daqiqa",
        "30m": "30 daqiqa",
        "1h": "1 soat",
        "6h": "6 soat",
        "12h": "12 soat",
        "1d": "1 kun",
        "7d": "7 kun",
        "permanent": "♾️ Cheksiz",
    }.get(value, value)


def _antilink_keyboard(cfg):
    enabled = bool(cfg.get("enabled", False))
    delete_enabled = bool(cfg.get("delete", True))
    action = cfg.get("action", "warn")

    rows = [
        [
            InlineKeyboardButton(
                "✅ Yoqilgan" if enabled else "❌ O‘chirilgan",
                callback_data="modmenu:antilink:toggle",
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Avto-o‘chirish: " + ("✅" if delete_enabled else "❌"),
                callback_data="modmenu:antilink:delete",
            )
        ],
        [
            InlineKeyboardButton(
                f"⚙️ Jazo: {_antilink_action_name(action)}",
                callback_data="modmenu:antilink:actions",
            )
        ],
    ]

    if action == "mute":
        rows.append([
            InlineKeyboardButton(
                f"⏱️ Mute: {_antilink_duration_name(cfg.get('mute_duration', '1h'))}",
                callback_data="modmenu:antilink:duration",
            )
        ])

    rows.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="modpage:1")
    ])
    return InlineKeyboardMarkup(rows)


def _antilink_actions_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚠️ Warn",
                callback_data="modmenu:antilink:setaction:warn",
            ),
            InlineKeyboardButton(
                "🔇 Mute",
                callback_data="modmenu:antilink:setaction:mute",
            ),
        ],
        [
            InlineKeyboardButton(
                "🚫 Ban",
                callback_data="modmenu:antilink:setaction:ban",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Ortga",
                callback_data="modmenu:antilink:back",
            )
        ],
    ])


def _antilink_duration_keyboard():
    values = [
        ("1m", "1 daqiqa"),
        ("5m", "5 daqiqa"),
        ("10m", "10 daqiqa"),
        ("30m", "30 daqiqa"),
        ("1h", "1 soat"),
        ("6h", "6 soat"),
        ("12h", "12 soat"),
        ("1d", "1 kun"),
        ("7d", "7 kun"),
        ("permanent", "♾️ Cheksiz"),
    ]

    rows = []
    for i in range(0, len(values), 2):
        row = []
        for value, label in values[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    f"⏱️ {label}",
                    callback_data=f"modmenu:antilink:setduration:{value}",
                )
            )
        rows.append(row)

    rows.append([
        InlineKeyboardButton(
            "🔙 Ortga",
            callback_data="modmenu:antilink:back",
        )
    ])
    return InlineKeyboardMarkup(rows)


def _antilink_text(cfg):
    enabled = "✅ Yoqilgan" if cfg.get("enabled") else "❌ O‘chirilgan"
    delete_enabled = "✅" if cfg.get("delete", True) else "❌"
    action = cfg.get("action", "warn")

    text = (
        "🔗 <b>Anti-Link</b>\n\n"
        f"Holat: <b>{enabled}</b>\n"
        f"🗑️ Avto-o‘chirish: <b>{delete_enabled}</b>\n"
        f"⚙️ Jazo: <b>{_antilink_action_name(action)}</b>\n"
    )

    if action == "mute":
        text += (
            f"⏱️ Mute muddati: "
            f"<b>{_antilink_duration_name(cfg.get('mute_duration', '1h'))}</b>\n"
        )

    if action == "ban":
        text += "\n🚫 Ban rejimi: 3 marta ogohlantiradi, 4-marta ban qiladi."

    return text


def _antilink_contains(message):
    text = message.text or message.caption or ""

    entities = []
    if message.entities:
        entities.extend(message.entities)
    if message.caption_entities:
        entities.extend(message.caption_entities)

    for entity in entities:
        if entity.type in ("url", "text_link"):
            return True

    lower = text.lower()

    markers = (
        "http://",
        "https://",
        "www.",
        "t.me/",
        "telegram.me/",
        "telegram.dog/",
    )

    if any(marker in lower for marker in markers):
        return True

    # Oddiy domenlarni ham ushlash
    import re
    return bool(
        re.search(
            r"(?:^|[\s(])(?:[a-z0-9-]+\.)+(?:com|net|org|uz|ru|me|io|xyz|site|online)(?:[/?#:]|$)",
            lower,
        )
    )


async def _antilink_apply_mute(update, context, user, duration_value):
    chat_id = update.effective_chat.id

    if duration_value == "permanent":
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        return "♾️ cheksiz"

    duration = _parse_duration(duration_value)
    if not duration:
        duration = timedelta(hours=1)

    until = datetime.now(timezone.utc) + duration

    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until,
    )
    return _antilink_duration_name(duration_value)


async def antilink_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or chat.type not in ("group", "supergroup"):
        return

    if not user or user.is_bot:
        return

    if message.text and message.text.startswith("/"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _antilink_config(mod)

    if not cfg.get("enabled", False):
        return

    # 👑 Adminlar himoyalangan
    if await _is_group_admin(update, context, user.id):
        return

    if not _antilink_contains(message):
        return

    # 🗑️ Linkni o‘chirish — jazo turidan qat'i nazar
    if cfg.get("delete", True):
        try:
            await message.delete()
        except TelegramError:
            pass

    action = cfg.get("action", "warn")
    uid = str(user.id)

    try:
        if action == "warn":
            warns = cfg.setdefault("warns", {})
            count = int(warns.get(uid, 0)) + 1
            warns[uid] = count
            save_data(data)

            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"⚠️ <b>Ogohlantirish</b>\n"
                    f"👤 {user.mention_html()}\n"
                    f"🔗 Link yuborish taqiqlangan.\n"
                    f"📊 Ogohlantirish: <b>{count}</b>"
                ),
                parse_mode="HTML",
            )

        elif action == "mute":
            duration_value = cfg.get("mute_duration", "1h")
            duration_text = await _antilink_apply_mute(
                update,
                context,
                user,
                duration_value,
            )

            mutes = mod.setdefault("mutes", {})
            mutes[uid] = {
                "actor_id": 0,
                "started": datetime.now(timezone.utc).isoformat(),
                "until": None if duration_value == "permanent"
                        else (
                            datetime.now(timezone.utc)
                            + (_parse_duration(duration_value) or timedelta(hours=1))
                        ).isoformat(),
                "duration": duration_value,
                "source": "antilink",
            }
            save_data(data)

            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"🔇 <b>Mute</b>\n"
                    f"👤 {user.mention_html()}\n"
                    f"🔗 Link yuborildi.\n"
                    f"⏱️ Muddati: <b>{duration_text}</b>"
                ),
                parse_mode="HTML",
            )

        else:
            violations = cfg.setdefault("violations", {})
            count = int(violations.get(uid, 0)) + 1

            if count < 4:
                violations[uid] = count
                save_data(data)

                await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        f"⚠️ <b>Anti-Link ogohlantirishi</b>\n"
                        f"👤 {user.mention_html()}\n"
                        f"🔗 Link yuborish taqiqlangan.\n"
                        f"🚫 Ban: <b>{count}/3</b>\n"
                        f"ℹ️ 4-marta link yuborilsa ban qilinadi."
                    ),
                    parse_mode="HTML",
                )
            else:
                await context.bot.ban_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                )
                violations[uid] = 0
                save_data(data)

                await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        f"🚫 <b>Ban</b>\n"
                        f"👤 {user.mention_html()}\n"
                        f"🔗 Anti-Link qoidasi 4-marta buzildi."
                    ),
                    parse_mode="HTML",
                )

    except TelegramError:
        # Botda kerakli Telegram huquqi bo‘lmasa, bot yiqilmasin.
        return


def _get_moderation_group(data, chat_id):
    gid = str(chat_id)
    groups = data.setdefault("groups", {})
    group = groups.setdefault(
        gid,
        {
            "chat_id": chat_id,
            "title": "Noma'lum guruh",
            "moderation": {},
        },
    )
    group.setdefault("moderation", {})
    mod = group["moderation"]
    mod.setdefault("warn_limit", 3)
    mod.setdefault("warns", {})
    return group, mod


async def _is_group_admin(update, context, user_id):
    chat = update.effective_chat

    if not chat:
        return False

    if is_admin(user_id):
        return True

    try:
        member = await context.bot.get_chat_member(chat.id, user_id)
        return member.status in ("creator", "administrator")
    except TelegramError:
        return False


async def _target_from_command(update, context):
    message = update.effective_message

    if not message:
        return None, None

    # 1️⃣ Reply orqali
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if target:
            return target.id, target

    args = context.args or []

    # 2️⃣ ID yoki username
    if not args:
        return None, None

    raw = args[0].strip()

    if raw.startswith("@"):
        # Telegram Bot API username -> user_id ni universal qidirishni bermaydi.
        return None, raw

    try:
        user_id = int(raw)
    except ValueError:
        return None, raw

    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            user_id,
        )
        return user_id, member.user
    except TelegramError:
        return user_id, None


def _warn_args(update, context, target_from_reply=False):
    args = context.args or []

    if target_from_reply:
        return " ".join(args).strip()

    if len(args) <= 1:
        return ""

    return " ".join(args[1:]).strip()


async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    if not message or not chat or not actor:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("⚠️ Bu buyruq faqat guruhda ishlaydi.")
        return

    if not await _is_group_admin(update, context, actor.id):
        await message.reply_text("🚫 Sizda moderatsiya huquqi yo‘q.")
        return

    target_id, target = await _target_from_command(update, context)

    if target_id is None:
        await message.reply_text(
            "⚠️ Foydalanuvchini ko‘rsating.\n\n"
            "Reply qilib:\n"
            "/warn sabab\n\n"
            "yoki:\n"
            "/warn USER_ID sabab"
        )
        return

    if target_id == actor.id:
        await message.reply_text("⚠️ O‘zingizga warn bera olmaysiz.")
        return

    if await _is_group_admin(update, context, target_id):
        await message.reply_text("🛡️ Adminlarga warn berish mumkin emas.")
        return

    reason = _warn_args(
        update,
        context,
        target_from_reply=bool(message.reply_to_message),
    )
    if not reason:
        reason = "Sabab ko‘rsatilmagan"

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)

    group["title"] = chat.title or "Guruh"

    uid = str(target_id)
    warns = mod["warns"].setdefault(uid, [])

    now = datetime.now(timezone.utc)
    warns.append(
        {
            "actor_id": actor.id,
            "reason": reason,
            "time": now.isoformat(),
        }
    )

    count = len(warns)
    limit = int(mod.get("warn_limit", 3))

    target_name = getattr(target, "first_name", None) if target else None
    target_name = target_name or str(target_id)

    if count >= limit:
        try:
            until = now + timedelta(hours=1)

            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=target_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )

            mod["warns"][uid] = []

            save_data(data)

            await message.reply_text(
                f"🔇 <b>{target_name}</b> 1 soatga mute qilindi.\n"
                f"⚠️ Warn limiti: {limit}/{limit}\n"
                f"📝 Sabab: {reason}",
                parse_mode="HTML",
            )
            return

        except TelegramError:
            save_data(data)

            await message.reply_text(
                f"⚠️ <b>{target_name}</b> warn oldi: "
                f"{count}/{limit}\n"
                f"📝 Sabab: {reason}\n\n"
                "❌ Avtomatik mute qilishning imkoni bo‘lmadi. "
                "Botda a’zolarni cheklash huquqi kerak.",
                parse_mode="HTML",
            )
            return

    save_data(data)

    await message.reply_text(
        f"⚠️ <b>{target_name}</b> warn oldi.\n"
        f"📊 Warn: {count}/{limit}\n"
        f"📝 Sabab: {reason}",
        parse_mode="HTML",
    )


async def warns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    if not message or not chat or not actor:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("⚠️ Bu buyruq faqat guruhda ishlaydi.")
        return

    if not await _is_group_admin(update, context, actor.id):
        await message.reply_text("🚫 Sizda moderatsiya huquqi yo‘q.")
        return

    target_id, target = await _target_from_command(update, context)

    if target_id is None:
        await message.reply_text(
            "📊 Warnlarni ko‘rish uchun reply qiling yoki USER_ID yozing."
        )
        return

    data = load_data()
    _, mod = _get_moderation_group(data, chat.id)

    warns = mod["warns"].get(str(target_id), [])
    limit = int(mod.get("warn_limit", 3))

    name = getattr(target, "first_name", None) if target else str(target_id)

    if not warns:
        await message.reply_text(
            f"📊 <b>{name}</b>\n"
            f"⚠️ Warn: 0/{limit}\n\n"
            "✅ Warn mavjud emas.",
            parse_mode="HTML",
        )
        return

    text = [
        f"📊 <b>{name}</b>",
        f"⚠️ Warn: {len(warns)}/{limit}",
        "",
    ]

    for i, item in enumerate(warns[-10:], 1):
        reason = item.get("reason", "Sabab ko‘rsatilmagan")
        text.append(f"{i}. ⚠️ {reason}")

    await message.reply_text("\n".join(text), parse_mode="HTML")


async def delwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    if not message or not chat or not actor:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("⚠️ Bu buyruq faqat guruhda ishlaydi.")
        return

    if not await _is_group_admin(update, context, actor.id):
        await message.reply_text("🚫 Sizda moderatsiya huquqi yo‘q.")
        return

    target_id, target = await _target_from_command(update, context)

    if target_id is None:
        await message.reply_text(
            "🗑️ Warn o‘chirish uchun reply qiling yoki USER_ID yozing."
        )
        return

    data = load_data()
    _, mod = _get_moderation_group(data, chat.id)

    uid = str(target_id)
    warns = mod["warns"].get(uid, [])

    if not warns:
        await message.reply_text("ℹ️ Bu foydalanuvchida warn yo‘q.")
        return

    removed = warns.pop()
    if not warns:
        mod["warns"].pop(uid, None)

    save_data(data)

    name = getattr(target, "first_name", None) if target else str(target_id)

    await message.reply_text(
        f"🗑️ <b>{name}</b> foydalanuvchisining oxirgi warningi o‘chirildi.\n"
        f"📊 Qolgan warn: {len(warns)}",
        parse_mode="HTML",
    )


async def resetwarns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    if not message or not chat or not actor:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("⚠️ Bu buyruq faqat guruhda ishlaydi.")
        return

    if not await _is_group_admin(update, context, actor.id):
        await message.reply_text("🚫 Sizda moderatsiya huquqi yo‘q.")
        return

    target_id, target = await _target_from_command(update, context)

    if target_id is None:
        await message.reply_text(
            "🔄 Warnlarni reset qilish uchun reply qiling yoki USER_ID yozing."
        )
        return

    data = load_data()
    _, mod = _get_moderation_group(data, chat.id)

    uid = str(target_id)
    mod["warns"].pop(uid, None)
    save_data(data)

    name = getattr(target, "first_name", None) if target else str(target_id)

    await message.reply_text(
        f"🔄 <b>{name}</b> foydalanuvchisining barcha warnlari reset qilindi.",
        parse_mode="HTML",
    )


# ============================================================
# 🔇 MUTE TIZIMI — 3-QADAM
# ============================================================

def _parse_duration(value):
    """10s, 10m, 2h, 1d formatlarini sekundga aylantiradi."""
    if not value:
        return None

    value = value.strip().lower()

    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    if len(value) < 2:
        return None

    unit = value[-1]
    number = value[:-1]

    if unit not in units:
        return None

    try:
        amount = int(number)
    except ValueError:
        return None

    if amount <= 0:
        return None

    seconds = amount * units[unit]

    # Juda uzoq yoki noto‘g‘ri muddatlardan himoya
    if seconds > 366 * 86400:
        return None

    return seconds


def _format_duration(seconds):
    if seconds % 86400 == 0:
        return f"{seconds // 86400} kun"
    if seconds % 3600 == 0:
        return f"{seconds // 3600} soat"
    if seconds % 60 == 0:
        return f"{seconds // 60} daqiqa"
    return f"{seconds} soniya"


async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    if not message or not chat or not actor:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("🔇 Bu buyruq faqat guruhda ishlaydi.")
        return

    if not await _is_group_admin(update, context, actor.id):
        await message.reply_text("🚫 Sizda moderatsiya huquqi yo‘q.")
        return

    target_id, target = await _target_from_command(update, context)

    if target_id is None:
        await message.reply_text(
            "🔇 Foydalanuvchini ko‘rsating.\n\n"
            "Reply qilib:\n"
            "/mute 10m\n\n"
            "yoki:\n"
            "/mute USER_ID 10m"
        )
        return

    # Reply bo‘lsa duration context.args[0], ID bo‘lsa context.args[1]
    args = context.args or []

    if message.reply_to_message:
        duration_raw = args[0] if args else None
    else:
        duration_raw = args[1] if len(args) >= 2 else None

    seconds = _parse_duration(duration_raw)

    if seconds is None:
        await message.reply_text(
            "⏱️ Muddat noto‘g‘ri.\n\n"
            "Masalan:\n"
            "🔹 /mute 10m\n"
            "🔹 /mute 2h\n"
            "🔹 /mute 1d\n"
            "🔹 /mute 30s"
        )
        return

    if target_id == actor.id:
        await message.reply_text("⚠️ O‘zingizni mute qila olmaysiz.")
        return

    if await _is_group_admin(update, context, target_id):
        await message.reply_text("🛡️ Adminlarni mute qilib bo‘lmaydi.")
        return

    now = datetime.now(timezone.utc)
    until = now + timedelta(seconds=seconds)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
    except TelegramError as e:
        text = str(e).lower()

        if "not enough rights" in text or "administrator" in text:
            await message.reply_text(
                "❌ Botda a’zolarni cheklash huquqi yo‘q.\n"
                "👑 Botga <b>Restrict Members</b> huquqini bering.",
                parse_mode="HTML",
            )
        else:
            await message.reply_text(
                "❌ Mute qilishda xatolik yuz berdi."
            )
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)

    group["title"] = chat.title or "Guruh"

    mutes = mod.setdefault("mutes", {})
    mutes[str(target_id)] = {
        "actor_id": actor.id,
        "started": now.isoformat(),
        "until": until.isoformat(),
        "duration": seconds,
    }

    save_data(data)

    name = getattr(target, "first_name", None) if target else str(target_id)

    await message.reply_text(
        f"🔇 <b>{name}</b> mute qilindi.\n"
        f"⏱️ Muddat: {_format_duration(seconds)}\n"
        f"🕐 Tugashi: {until.strftime('%Y-%m-%d %H:%M UTC')}",
        parse_mode="HTML",
    )


async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    if not message or not chat or not actor:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("🔊 Bu buyruq faqat guruhda ishlaydi.")
        return

    if not await _is_group_admin(update, context, actor.id):
        await message.reply_text("🚫 Sizda moderatsiya huquqi yo‘q.")
        return

    target_id, target = await _target_from_command(update, context)

    if target_id is None:
        await message.reply_text(
            "🔊 Foydalanuvchini ko‘rsating.\n\n"
            "Reply qilib:\n"
            "/unmute\n\n"
            "yoki:\n"
            "/unmute USER_ID"
        )
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
    except TelegramError:
        await message.reply_text(
            "❌ Unmute qilishda xatolik yuz berdi.\n"
            "Botning guruhdagi huquqlarini tekshiring."
        )
        return

    data = load_data()
    _, mod = _get_moderation_group(data, chat.id)

    mutes = mod.setdefault("mutes", {})
    mutes.pop(str(target_id), None)

    save_data(data)

    name = getattr(target, "first_name", None) if target else str(target_id)

    await message.reply_text(
        f"🔊 <b>{name}</b> unmute qilindi.",
        parse_mode="HTML",
    )


# ==================== BAN / UNBAN / KICK ====================

def _ban_duration(value):
    if not value:
        return None
    value = value.strip().lower()
    if len(value) < 2:
        return None
    try:
        number = int(value[:-1])
        unit = value[-1]
        if number <= 0:
            return None
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if unit not in multipliers:
            return None
        seconds = number * multipliers[unit]
        if seconds > 366 * 86400:
            return None
        return seconds
    except (ValueError, TypeError):
        return None


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    actor = update.effective_user
    chat_id = update.effective_chat.id

    if not await _is_group_admin(update, context, actor.id):
        await update.message.reply_text("🛡️ Bu buyruqdan faqat adminlar foydalanishi mumkin.")
        return

    target = await _target_from_command(update, context)
    if not target:
        await update.message.reply_text(
            "⚠️ Foydalanuvchini reply qiling yoki User ID kiriting.\n\n"
            "Misol:\n"
            "🚫 /ban\n"
            "🚫 /ban 1h\n"
            "🚫 /ban 7d"
        )
        return

    target_id = target[0]
    target_name = target[1]

    if target_id == actor.id:
        await update.message.reply_text("🛡️ O‘zingizni ban qila olmaysiz.")
        return

    if await _is_group_admin(update, context, target_id):
        await update.message.reply_text("👑 Adminni ban qilish mumkin emas.")
        return

    args = list(context.args or [])

    # Reply: /ban [duration]
    # ID: /ban USER_ID [duration]
    duration_text = None
    if update.message.reply_to_message:
        if args:
            duration_text = args[0]
    else:
        if len(args) >= 2:
            duration_text = args[1]

    seconds = _ban_duration(duration_text)

    if duration_text and seconds is None:
        await update.message.reply_text(
            "⚠️ Vaqt noto‘g‘ri.\n"
            "Misollar: `10m`, `1h`, `1d`, `7d`"
        )
        return

    try:
        if seconds is None:
            # ♾️ Permanent ban
            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_id,
            )
            duration_label = "♾️ Cheksiz"
            until = None
        else:
            until_dt = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                until_date=until_dt,
            )
            duration_label = f"⏱️ {duration_text}"
            until = until_dt.isoformat()

        data = load_data()
        group, mod = _get_moderation_group(data, chat_id)
        group.setdefault("bans", {})
        group["bans"][str(target_id)] = {
            "actor_id": actor.id,
            "started": datetime.now(timezone.utc).isoformat(),
            "until": until,
            "duration": duration_label,
            "type": "temporary" if seconds else "permanent",
        }
        save_data(data)

        await update.message.reply_text(
            f"🚫 <b>{target_name}</b> ban qilindi.\n"
            f"⏳ Muddat: <b>{duration_label}</b>",
            parse_mode="HTML",
        )

    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Ban qilishda xato: {e}"
        )


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    actor = update.effective_user
    chat_id = update.effective_chat.id

    if not await _is_group_admin(update, context, actor.id):
        await update.message.reply_text("🛡️ Bu buyruqdan faqat adminlar foydalanishi mumkin.")
        return

    target = await _target_from_command(update, context)
    if not target:
        await update.message.reply_text(
            "⚠️ Foydalanuvchini reply qiling yoki User ID kiriting."
        )
        return

    target_id = target[0]
    target_name = target[1]

    try:
        await context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=target_id,
            only_if_banned=True,
        )

        data = load_data()
        group, mod = _get_moderation_group(data, chat_id)
        group.setdefault("bans", {})
        group["bans"].pop(str(target_id), None)
        save_data(data)

        await update.message.reply_text(
            f"🔓 <b>{target_name}</b> ban’dan chiqarildi.",
            parse_mode="HTML",
        )

    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Unban qilishda xato: {e}"
        )


async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    actor = update.effective_user
    chat_id = update.effective_chat.id

    if not await _is_group_admin(update, context, actor.id):
        await update.message.reply_text("🛡️ Bu buyruqdan faqat adminlar foydalanishi mumkin.")
        return

    target = await _target_from_command(update, context)
    if not target:
        await update.message.reply_text(
            "⚠️ Foydalanuvchini reply qiling yoki User ID kiriting."
        )
        return

    target_id = target[0]
    target_name = target[1]

    if target_id == actor.id:
        await update.message.reply_text("🛡️ O‘zingizni kick qila olmaysiz.")
        return

    if await _is_group_admin(update, context, target_id):
        await update.message.reply_text("👑 Adminni kick qilish mumkin emas.")
        return

    try:
        # Telegramda kick qilish uchun ban qilib, darhol unban qilamiz.
        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=target_id,
        )
        await context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=target_id,
        )

        data = load_data()
        group, mod = _get_moderation_group(data, chat_id)
        group.setdefault("kicks", [])
        group["kicks"].append({
            "user_id": target_id,
            "actor_id": actor.id,
            "time": datetime.now(timezone.utc).isoformat(),
        })
        save_data(data)

        await update.message.reply_text(
            f"👢 <b>{target_name}</b> guruhdan chiqarildi.",
            parse_mode="HTML",
        )

    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Kick qilishda xato: {e}"
        )


# ==================== 👑 GROUP MODERATION ADMINS ====================


ADMIN_RIGHTS = {
    "change_info": "⚙️ Guruh ma’lumotini o‘zgartirish",
    "delete": "🗑️ Xabarlarni o‘chirish",
    "restrict": "🚫 Foydalanuvchilarni bloklash",
    "invite": "➕ Foydalanuvchilarni qo‘shish",
    "pin": "📌 Xabarlarni qadash",
    "tags": "🏷️ A’zo teglarini tahrirlash",
    "stories": "📖 Hikoyalarni boshqarish",
    "video": "📺 Jonli efirlarni boshqarish",
    "promote": "👑 Yangi adminlar qo‘shish",
    "anonymous": "🕵️ Anonimlik",
}

def _admin_rights_keyboard(rights):
    def mark(key):
        return "✅" if rights.get(key, False) else "❌"

    rows = [
        [InlineKeyboardButton(f"{mark('change_info')} ⚙️ Guruh ma’lumoti", callback_data="adminright:change_info")],
        [InlineKeyboardButton(f"{mark('delete')} 🗑️ Xabarlarni o‘chirish", callback_data="adminright:delete")],
        [InlineKeyboardButton(f"{mark('restrict')} 🚫 Foydalanuvchilarni bloklash", callback_data="adminright:restrict")],
        [InlineKeyboardButton(f"{mark('invite')} ➕ Foydalanuvchilarni qo‘shish", callback_data="adminright:invite")],
        [InlineKeyboardButton(f"{mark('pin')} 📌 Xabarlarni qadash", callback_data="adminright:pin")],
        [InlineKeyboardButton(f"{mark('tags')} 🏷️ A’zo teglarini tahrirlash", callback_data="adminright:tags")],
        [InlineKeyboardButton(f"{mark('stories')} 📖 Hikoyalarni boshqarish", callback_data="adminright:stories")],
        [InlineKeyboardButton(f"{mark('video')} 📺 Jonli efirlarni boshqarish", callback_data="adminright:video")],
        [InlineKeyboardButton(f"{mark('promote')} 👑 Yangi adminlar qo‘shish", callback_data="adminright:promote")],
        [InlineKeyboardButton(f"{mark('anonymous')} 🕵️ Anonimlik", callback_data="adminright:anonymous")],
        [
            InlineKeyboardButton("💾 Tasdiqlash", callback_data="adminright:save"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="adminright:cancel"),
        ],
    ]
    return InlineKeyboardMarkup(rows)




# ============================================================
# 🗑️ MESSAGE MANAGEMENT
# ============================================================

async def _message_mod_permission(update, context):
    """Faqat haqiqiy Telegram admin yoki global bot admin."""
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or chat.type not in ("group", "supergroup"):
        return False

    return await _is_group_admin(update, context, user.id)


async def _target_message_is_admin(update, context, message):
    """Reply qilingan xabar egasi admin bo'lsa True."""
    if not message or not message.from_user:
        return False

    return await _is_group_admin(
        update,
        context,
        message.from_user.id,
    )



# ============================================================
# 🔒 LOCK / UNLOCK
# ============================================================

LOCK_TYPES = {
    "text": "💬 Matn",
    "photo": "🖼️ Rasm",
    "video": "🎥 Video",
    "audio": "🎵 Audio",
    "document": "📄 Fayl",
    "voice": "🎤 Voice",
    "sticker": "🎭 Sticker",
    "gif": "🎞️ GIF",
    "link": "🔗 Link",
    "all": "🔒 Hammasi",
}


def _lock_mod(update, context):
    chat = update.effective_chat
    return chat and chat.type in ("group", "supergroup")


async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔒 Guruhdagi kontent turini bloklash."""
    message = update.effective_message

    if not _lock_mod(update, context):
        await message.reply_text("🛡️ Bu buyruqni guruh ichida ishlating.")
        return

    if not await _is_group_admin(update, context, update.effective_user.id):
        await message.reply_text("🚫 Sizda Lock huquqi yo‘q.")
        return

    if not context.args:
        names = "\n".join(
            f"• `{key}` — {value}"
            for key, value in LOCK_TYPES.items()
        )
        await message.reply_text(
            "🔒 <b>LOCK</b>\n\n"
            "Bloklash turini yozing:\n\n"
            f"{names}\n\n"
            "Misol: `/lock photo`",
            parse_mode="HTML",
        )
        return

    lock_type = context.args[0].lower().strip()

    if lock_type not in LOCK_TYPES:
        await message.reply_text(
            "❌ Noto‘g‘ri tur.\n\n"
            "Masalan: `/lock text`, `/lock photo`, `/lock link` yoki `/lock all`"
        )
        return

    data = load_data()
    group, mod = _get_moderation_group(data, message.chat_id)

    locks = mod.setdefault("locks", {})

    if lock_type == "all":
        for key in LOCK_TYPES:
            if key != "all":
                locks[key] = True
    else:
        locks[lock_type] = True

    save_data(data)

    await message.reply_text(
        f"🔒 {LOCK_TYPES[lock_type]} bloklandi."
    )


async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔓 Guruhdagi kontent turiga qayta ruxsat berish."""
    message = update.effective_message

    if not _lock_mod(update, context):
        await message.reply_text("🛡️ Bu buyruqni guruh ichida ishlating.")
        return

    if not await _is_group_admin(update, context, update.effective_user.id):
        await message.reply_text("🚫 Sizda Unlock huquqi yo‘q.")
        return

    if not context.args:
        names = "\n".join(
            f"• `{key}` — {value}"
            for key, value in LOCK_TYPES.items()
        )
        await message.reply_text(
            "🔓 <b>UNLOCK</b>\n\n"
            "Qayta ruxsat berish turini yozing:\n\n"
            f"{names}\n\n"
            "Misol: `/unlock photo`",
            parse_mode="HTML",
        )
        return

    lock_type = context.args[0].lower().strip()

    if lock_type not in LOCK_TYPES:
        await message.reply_text(
            "❌ Noto‘g‘ri tur.\n\n"
            "Masalan: `/unlock text`, `/unlock photo`, `/unlock link` yoki `/unlock all`"
        )
        return

    data = load_data()
    group, mod = _get_moderation_group(data, message.chat_id)

    locks = mod.setdefault("locks", {})

    if lock_type == "all":
        for key in LOCK_TYPES:
            if key != "all":
                locks[key] = False
    else:
        locks[lock_type] = False

    save_data(data)

    await message.reply_text(
        f"🔓 {LOCK_TYPES[lock_type]} qayta ruxsat etildi."
    )


def _message_lock_type(message):
    """Xabarning qaysi lock turiga tegishli ekanini aniqlaydi."""

    if message.text:
        return "text"

    if message.photo:
        return "photo"

    if message.video:
        return "video"

    if message.audio:
        return "audio"

    if message.document:
        return "document"

    if message.voice:
        return "voice"

    if message.sticker:
        return "sticker"

    if message.animation:
        return "gif"

    return None


def _contains_link(message):
    """Matn/caption ichida URL borligini tekshiradi."""
    entities = list(message.entities or [])
    entities += list(message.caption_entities or [])

    for entity in entities:
        if entity.type in ("url", "text_link"):
            return True

    text = message.text or message.caption or ""

    lowered = text.lower()

    return (
        "http://" in lowered
        or "https://" in lowered
        or "www." in lowered
        or "t.me/" in lowered
    )


async def moderation_lock_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🔒 Lock yoqilgan kontentni oddiy a'zolardan o‘chiradi.
    Lock o‘chiq bo‘lsa hech narsa qilmaydi.
    """

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    if chat.type not in ("group", "supergroup"):
        return

    # 👑 Adminlar lockdan himoyalangan
    if await _is_group_admin(update, context, user.id):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)

    locks = mod.setdefault("locks", {})

    msg_type = _message_lock_type(message)

    blocked = False

    if msg_type and locks.get(msg_type, False):
        blocked = True

    if locks.get("link", False) and _contains_link(message):
        blocked = True

    if blocked:
        try:
            await context.bot.delete_message(
                chat_id=chat.id,
                message_id=message.message_id,
            )
        except TelegramError:
            pass

async def del_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🗑️ Reply qilingan bitta xabarni o'chirish."""
    message = update.effective_message

    if not await _message_mod_permission(update, context):
        await message.reply_text("🚫 Sizda xabar o‘chirish huquqi yo‘q.")
        return

    if not message.reply_to_message:
        await message.reply_text(
            "ℹ️ O‘chirish uchun xabarga reply qilib `/del` yozing."
        )
        return

    target = message.reply_to_message

    if await _target_message_is_admin(update, context, target):
        await message.reply_text(
            "👑 Adminning xabarini o‘chirishga ruxsat berilmaydi."
        )
        return

    try:
        await context.bot.delete_message(
            chat_id=message.chat_id,
            message_id=target.message_id,
        )

        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id,
            )
        except TelegramError:
            pass

    except TelegramError as e:
        await message.reply_text(
            f"❌ Xabarni o‘chirib bo‘lmadi.\n\n"
            f"Sabab: `{e}`"
        )


async def purge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧹 Replydan boshlab bir nechta xabarni o'chirish."""
    message = update.effective_message

    if not await _message_mod_permission(update, context):
        await message.reply_text("🚫 Sizda xabarlarni tozalash huquqi yo‘q.")
        return

    if not message.reply_to_message:
        await message.reply_text(
            "ℹ️ Boshlang‘ich xabarga reply qilib `/purge 10` yozing."
        )
        return

    count = 10

    if context.args:
        try:
            count = int(context.args[0])
        except ValueError:
            await message.reply_text(
                "❌ Miqdor son bo‘lishi kerak.\nMasalan: `/purge 20`"
            )
            return

    count = max(1, min(count, 100))

    start_id = message.reply_to_message.message_id
    end_id = message.message_id

    if start_id > end_id:
        await message.reply_text("❌ Xabar oralig‘i noto‘g‘ri.")
        return

    ids = list(range(start_id, min(end_id, start_id + count - 1) + 1))

    deleted = 0
    skipped = 0

    for message_id in ids:
        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message_id,
            )
            deleted += 1
        except TelegramError:
            skipped += 1

    try:
        await context.bot.delete_message(
            chat_id=message.chat_id,
            message_id=message.message_id,
        )
    except TelegramError:
        pass

    if deleted == 0:
        await message.reply_text(
            "❌ Hech qanday xabar o‘chirilmadi."
        )


async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📌 Reply qilingan xabarni qadash."""
    message = update.effective_message

    if not await _message_mod_permission(update, context):
        await message.reply_text("🚫 Sizda xabar qadash huquqi yo‘q.")
        return

    if not message.reply_to_message:
        await message.reply_text(
            "ℹ️ Qadash uchun xabarga reply qilib `/pin` yozing."
        )
        return

    target = message.reply_to_message

    try:
        await context.bot.pin_chat_message(
            chat_id=message.chat_id,
            message_id=target.message_id,
            disable_notification=False,
        )

        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id,
            )
        except TelegramError:
            pass

    except TelegramError as e:
        await message.reply_text(
            f"❌ Xabarni qadab bo‘lmadi.\n\n"
            f"Sabab: `{e}`"
        )


async def unpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📍 Reply qilingan xabarni unpin qilish."""
    message = update.effective_message

    if not await _message_mod_permission(update, context):
        await message.reply_text("🚫 Sizda xabar unpin qilish huquqi yo‘q.")
        return

    try:
        if message.reply_to_message:
            await context.bot.unpin_chat_message(
                chat_id=message.chat_id,
                message_id=message.reply_to_message.message_id,
            )
        else:
            await context.bot.unpin_chat_message(
                chat_id=message.chat_id,
            )

        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id,
            )
        except TelegramError:
            pass

    except TelegramError as e:
        await message.reply_text(
            f"❌ Unpin qilib bo‘lmadi.\n\n"
            f"Sabab: `{e}`"
        )


async def adminn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    actor_id = update.effective_user.id

    # Faqat haqiqiy Telegram guruh admini yoki botning global admini
    if not is_admin(actor_id):
        try:
            member = await context.bot.get_chat_member(
                update.effective_chat.id,
                actor_id,
            )
            if member.status not in ("creator", "administrator"):
                await update.message.reply_text(
                    "⛔ Bu buyruqni faqat guruh yoki bot administratori ishlata oladi."
                )
                return
        except TelegramError:
            await update.message.reply_text(
                "❌ Admin huquqini tekshirib bo‘lmadi."
            )
            return

    target = await _target_from_command(update, context)

    if not target:
        await update.message.reply_text(
            "⚠️ Foydalanuvchini reply qiling yoki User ID kiriting.\n\n"
            "Misol: 👑 /adminn 123456789"
        )
        return

    target_id, target_user = target

    if target_id == actor_id:
        await update.message.reply_text(
            "⚠️ O‘zingizni qayta admin qilish shart emas."
        )
        return

    # Foydalanuvchi guruhda ekanini tekshirish
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            target_id,
        )
        if member.status in ("left", "kicked"):
            await update.message.reply_text(
                "⚠️ Bu foydalanuvchi guruhda emas."
            )
            return
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Foydalanuvchini tekshirib bo‘lmadi: {e}"
        )
        return

    context.user_data["adminn_target"] = {
        "chat_id": update.effective_chat.id,
        "target_id": target_id,
        "target_name": target_user.full_name,
        "actor_id": actor_id,
    }

    context.user_data["adminn_rights"] = {
        "change_info": False,
        "delete": False,
        "restrict": False,
        "invite": False,
        "pin": False,
        "tags": False,
        "stories": False,
        "video": False,
        "promote": False,
        "anonymous": False,
    }

    await update.message.reply_text(
        f"👑 <b>{target_user.full_name}</b> uchun admin huquqlarini tanlang.\n\n"
        "Har bir tugmani bosib huquqni yoqing yoki o‘chiring.\n"
        "So‘ngra 💾 <b>Tasdiqlash</b> ni bosing.",
        parse_mode="HTML",
        reply_markup=_admin_rights_keyboard(
            context.user_data["adminn_rights"]
        ),
    )


async def adminn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    target = context.user_data.get("adminn_target")
    rights = context.user_data.get("adminn_rights")

    if not target or not rights:
        await query.edit_message_text(
            "⚠️ Admin tayinlash sessiyasi tugagan. /adminn ni qayta boshlang."
        )
        return

    # Faqat /adminn ni boshlagan admin boshqara oladi
    if query.from_user.id != target["actor_id"]:
        await query.answer(
            "⛔ Bu panelni faqat uni ochgan admin boshqara oladi.",
            show_alert=True,
        )
        return

    action = query.data.split(":", 1)[1]

    if action in rights:
        rights[action] = not rights[action]

        await query.edit_message_reply_markup(
            reply_markup=_admin_rights_keyboard(rights)
        )
        return

    if action == "cancel":
        context.user_data.pop("adminn_target", None)
        context.user_data.pop("adminn_rights", None)

        await query.edit_message_text(
            "❌ Admin tayinlash bekor qilindi."
        )
        return

    if action == "save":
        try:
            await context.bot.promote_chat_member(
                chat_id=target["chat_id"],
                user_id=target["target_id"],

                is_anonymous=rights["anonymous"],
                can_manage_chat=False,
                can_delete_messages=rights["delete"],
                can_manage_video_chats=rights["video"],
                can_restrict_members=rights["restrict"],
                can_promote_members=rights["promote"],
                can_change_info=rights["change_info"],
                can_invite_users=rights["invite"],

                can_post_stories=rights["stories"],
                can_edit_stories=rights["stories"],
                can_delete_stories=rights["stories"],

                can_post_messages=False,
                can_edit_messages=False,
                can_pin_messages=rights["pin"],
                can_manage_topics=False,
                can_manage_direct_messages=False,
                can_manage_tags=rights["tags"],
            )

            selected = [
                label
                for key, label in ADMIN_RIGHTS.items()
                if rights.get(key)
            ]

            text = (
                f"✅ <b>{target['target_name']}</b> Telegram guruhida admin qilindi.\n\n"
                "👑 <b>Berilgan huquqlar:</b>\n"
            )

            if selected:
                text += "\n".join(f"• {x}" for x in selected)
            else:
                text += "• ❌ Maxsus huquq tanlanmadi."

            await query.edit_message_text(
                text,
                parse_mode="HTML",
            )

            context.user_data.pop("adminn_target", None)
            context.user_data.pop("adminn_rights", None)

        except TelegramError as e:
            await query.edit_message_text(
                "❌ Admin qilish amalga oshmadi.\n\n"
                "Bot guruhda administrator bo‘lishi va boshqa adminlarni "
                f"tayinlash huquqiga ega bo‘lishi kerak.\n\n"
                f"Telegram xatosi: {e}"
            )


async def unadminn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    actor_id = update.effective_user.id

    if not is_admin(actor_id):
        try:
            member = await context.bot.get_chat_member(
                update.effective_chat.id,
                actor_id,
            )
            if member.status not in ("creator", "administrator"):
                await update.message.reply_text(
                    "⛔ Bu buyruqni faqat guruh yoki bot administratori ishlata oladi."
                )
                return
        except TelegramError:
            return

    target = await _target_from_command(update, context)

    if not target:
        await update.message.reply_text(
            "⚠️ Foydalanuvchini reply qiling yoki User ID kiriting."
        )
        return

    target_id, target_user = target

    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_id,

            is_anonymous=False,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,

            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,

            can_post_messages=False,
            can_edit_messages=False,
            can_pin_messages=False,
            can_manage_topics=False,
            can_manage_direct_messages=False,
            can_manage_tags=False,
        )

        await update.message.reply_text(
            f"❌ <b>{target_user.full_name}</b> adminlikdan chiqarildi.",
            parse_mode="HTML",
        )

    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Adminlikni olib tashlab bo‘lmadi: {e}"
        )


# ============================================================
# 🌊 ANTI-FLOOD MESSAGE HANDLER
# ============================================================

async def antiflood_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    if chat.type not in ("group", "supergroup"):
        return

    # Buyruqlar flood hisobiga kirmaydi
    if getattr(message, "text", None) and str(message.text).startswith("/"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _antiflood_config(mod)

    if not cfg.get("enabled", False):
        return

    # Telegram adminlari flooddan himoyalangan
    if await _is_group_admin(update, context, user.id):
        return

    limit = max(2, min(int(cfg.get("limit", 5)), 50))
    window = max(1, min(int(cfg.get("window", 3)), 60))

    now = datetime.now(timezone.utc).timestamp()
    key = (chat.id, user.id)

    timestamps = ANTIFLOOD_RUNTIME.setdefault(key, [])
    timestamps[:] = [t for t in timestamps if now - t <= window]
    timestamps.append(now)

    if len(timestamps) <= limit:
        return

    try:
        await message.delete()
    except TelegramError:
        pass

    # Juda ko‘p eski timestamp yig‘ilib qolmasin
    timestamps[:] = timestamps[-limit:]


# ============================================================
# 📢 ANTI-REKLAMA
# ============================================================

def _antireklama_config(mod):
    cfg = mod.setdefault("antireklama", {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("delete", True)
    cfg.setdefault("action", "warn")
    cfg.setdefault("mute_duration", "600")
    cfg.setdefault("warns", {})
    cfg.setdefault("violations", {})
    return cfg


def _antireklama_action_name(action):
    return {
        "warn": "⚠️ Warn",
        "mute": "🔇 Mute",
        "ban": "🚫 Ban",
    }.get(action, "⚠️ Warn")


def _antireklama_duration_name(value):
    return {
        "60": "1 daqiqa",
        "300": "5 daqiqa",
        "600": "10 daqiqa",
        "1800": "30 daqiqa",
        "3600": "1 soat",
        "21600": "6 soat",
        "43200": "12 soat",
        "86400": "1 kun",
        "604800": "7 kun",
        "permanent": "♾️ Doimiy",
    }.get(str(value), "10 daqiqa")


def _antireklama_keyboard(cfg):
    status = "✅ Yoqilgan" if cfg.get("enabled") else "❌ O‘chirilgan"
    delete = "✅ Yoqilgan" if cfg.get("delete", True) else "❌ O‘chirilgan"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                status,
                callback_data="modmenu:antireklama:toggle",
            )
        ],
        [
            InlineKeyboardButton(
                f"🗑️ Avto-o‘chirish: {delete}",
                callback_data="modmenu:antireklama:delete",
            )
        ],
        [
            InlineKeyboardButton(
                f"⚖️ Jazo: {_antireklama_action_name(cfg.get('action', 'warn'))}",
                callback_data="modmenu:antireklama:actions",
            )
        ],
        [
            InlineKeyboardButton(
                f"⏱️ Mute: {_antireklama_duration_name(cfg.get('mute_duration', '600'))}",
                callback_data="modmenu:antireklama:duration",
            )
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modpage:1"),
        ],
    ])


def _antireklama_actions_keyboard(cfg):
    current = cfg.get("action", "warn")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{'🔘' if current == 'warn' else '⚪'} ⚠️ Warn",
                callback_data="modmenu:antireklama:setaction:warn",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'🔘' if current == 'mute' else '⚪'} 🔇 Mute",
                callback_data="modmenu:antireklama:setaction:mute",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'🔘' if current == 'ban' else '⚪'} 🚫 Ban",
                callback_data="modmenu:antireklama:setaction:ban",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Anti-Reklama",
                callback_data="modmenu:antireklama:back",
            )
        ],
    ])


def _antireklama_duration_keyboard(cfg):
    current = str(cfg.get("mute_duration", "600"))
    values = [
        ("60", "1 daqiqa"),
        ("300", "5 daqiqa"),
        ("600", "10 daqiqa"),
        ("1800", "30 daqiqa"),
        ("3600", "1 soat"),
        ("21600", "6 soat"),
        ("43200", "12 soat"),
        ("86400", "1 kun"),
        ("604800", "7 kun"),
        ("permanent", "♾️ Doimiy"),
    ]

    rows = []
    row = []

    for value, label in values:
        mark = "🔘" if current == value else "⚪"
        row.append(
            InlineKeyboardButton(
                f"{mark} {label}",
                callback_data=f"modmenu:antireklama:setduration:{value}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton(
            "🔙 Anti-Reklama",
            callback_data="modmenu:antireklama:back",
        )
    ])

    return InlineKeyboardMarkup(rows)


def _antireklama_text(cfg, title):
    status = "✅ Yoqilgan" if cfg.get("enabled") else "❌ O‘chirilgan"
    delete = "✅ Yoqilgan" if cfg.get("delete", True) else "❌ O‘chirilgan"

    return (
        f"📢 *Anti-Reklama*\n\n"
        f"👥 Guruh: *{title}*\n"
        f"📌 Holat: {status}\n"
        f"🗑️ Avto-o‘chirish: {delete}\n"
        f"⚖️ Jazo: {_antireklama_action_name(cfg.get('action', 'warn'))}\n"
        f"⏱️ Mute davomiyligi: {_antireklama_duration_name(cfg.get('mute_duration', '600'))}\n\n"
        f"🔎 Reklama bir nechta belgilar kombinatsiyasi orqali aniqlanadi."
    )


def _antireklama_score(message):
    text = (message.text or message.caption or "").strip()
    if not text:
        return 0

    low = text.lower()
    score = 0

    # 📢 Savdo/xizmat/reklama belgilar
    promo_words = (
        "sotiladi", "sotib oling", "buyurtma", "zakaz",
        "aksiya", "chegirma", "narxi", "narx",
        "xizmat", "reklama", "mijoz", "murojaat",
        "obuna", "qo‘shiling", "qo'shiling",
        "kanalimiz", "guruhimiz", "kurs",
        "daromad", "pul ishlang", "ishlab toping",
        "100% daromad", "foyda",
    )

    has_promo = any(word in low for word in promo_words)
    if has_promo:
        score += 1

    # 💰 Narx / pul belgisi
    has_price = bool(re.search(
        r"(?<!\d)\d[\d\s.,]*\s*(so['’`]?m|sum|uzs|usd|\$|€|eur|руб|rub|₽)\b",
        low,
    ))
    if has_price:
        score += 1

    # 📞 Telefon
    has_phone = bool(re.search(
        r"(?:\+?998[\s\-()]*)?(?:\d[\s\-()]*){9,12}",
        text,
    ))
    if has_phone:
        score += 1

    # 👤 Telegram username
    has_username = bool(re.search(
        r"(?<!\w)@[A-Za-z0-9_]{4,}",
        text,
    ))
    if has_username:
        score += 1

    # 📣 Reklama chaqirig‘i
    cta_words = (
        "yozing", "bog‘laning", "bog'laning",
        "menga yozing", "aloqa", "murojaat qiling",
        "buyurtma bering", "hoziroq oling",
        "qo‘shiling", "qo'shiling",
        "link orqali", "havola orqali",
    )

    has_cta = any(word in low for word in cta_words)
    if has_cta:
        score += 1

    # 🔗 Link
    has_link = bool(re.search(
        r"(https?://|www\.|t\.me/|telegram\.me/|telegram\.dog/)",
        low,
    ))
    if has_link:
        score += 1

    # 🛒 Raqam + savdo/xizmat
    has_sale_number = bool(
        re.search(r"\b\d{2,}\b", low)
        and any(
            word in low
            for word in (
                "sotiladi", "xizmat", "kurs",
                "narx", "chegirma", "buyurtma", "zakaz",
            )
        )
    )
    if has_sale_number:
        score += 1

    # 🚨 Kuchli reklama kombinatsiyalari
    strong_ad = (
        (has_promo and has_cta)
        or (has_promo and has_username)
        or (has_promo and has_link)
        or (has_price and has_promo)
        or (has_phone and has_cta)
        or (has_username and has_cta)
        or (has_link and has_cta)
        or has_sale_number
    )

    if strong_ad:
        return max(score, 2)

    # Oddiy username, oddiy narx yoki bitta reklama so‘zi
    # o‘zi bilan jazo bermaydi.
    return score


def _antireklama_is_ad(message):
    return _antireklama_score(message) >= 2


async def antireklama_message(update, context):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or chat.type not in ("group", "supergroup"):
        return

    if not user or user.is_bot:
        return

    if message.text and message.text.startswith("/"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _antireklama_config(mod)

    if not cfg.get("enabled", False):
        return

    # Adminlar reklama filtridan himoyalangan
    if await _is_group_admin(update, context, user.id):
        return

    if not _antireklama_is_ad(message):
        return

    # Har bir reklama xabari avval o‘chiriladi
    if cfg.get("delete", True):
        try:
            await message.delete()
        except TelegramError:
            pass

    uid = str(user.id)

    violations = cfg.setdefault("violations", {})
    violations[uid] = int(violations.get(uid, 0)) + 1
    count = violations[uid]

    action = cfg.get("action", "warn")

    # WARN
    if action == "warn":
        warns = cfg.setdefault("warns", {})
        warns[uid] = int(warns.get(uid, 0)) + 1

        try:
            sent = await context.bot.send_message(
                chat.id,
                f"⚠️ {user.mention_html()} reklama yuborgani uchun ogohlantirildi.\n"
                f"📊 Reklama ogohlantirishlari: {warns[uid]}",
                parse_mode="HTML",
            )
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                8,
            )
        except Exception:
            pass

    # MUTE
    elif action == "mute":
        duration = str(cfg.get("mute_duration", "600"))

        try:
            permissions = ChatPermissions(can_send_messages=False)

            if duration == "permanent":
                await context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=permissions,
                )
            else:
                seconds = max(1, int(duration))
                until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
                await context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=permissions,
                    until_date=until,
                )

            try:
                sent = await context.bot.send_message(
                    chat.id,
                    f"🔇 {user.mention_html()} reklama yuborgani uchun "
                    f"mute qilindi.\n⏱️ {_antireklama_duration_name(duration)}",
                    parse_mode="HTML",
                )
                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                    8,
                )
            except Exception:
                pass

        except TelegramError:
            pass

    # BAN
    elif action == "ban":
        try:
            await context.bot.ban_chat_member(
                chat.id,
                user.id,
            )

            try:
                sent = await context.bot.send_message(
                    chat.id,
                    f"🚫 {user.mention_html()} reklama yuborgani uchun ban qilindi.",
                    parse_mode="HTML",
                )
                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                    8,
                )
            except Exception:
                pass

        except TelegramError:
            pass

    save_data(data)



# ============================================================
# 🔁 ANTI-REPEAT — 10-BOSQICH
# ============================================================

def _antirepeat_config(mod):
    cfg = mod.setdefault("antirepeat", {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("delete", True)
    cfg.setdefault("threshold", 3)
    cfg.setdefault("window", 10)
    cfg.setdefault("action", "warn")
    cfg.setdefault("mute_duration", "600")
    cfg.setdefault("violations", {})
    cfg.setdefault("warns", {})
    return cfg


def _antirepeat_keyboard(cfg):
    status = "✅ Yoqilgan" if cfg.get("enabled", False) else "❌ O‘chirilgan"
    delete = "✅ Yoqilgan" if cfg.get("delete", True) else "❌ O‘chirilgan"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{status}",
                callback_data="modmenu:antirepeat:toggle",
            ),
        ],
        [
            InlineKeyboardButton(
                f"🗑️ Avto-o‘chirish: {delete}",
                callback_data="modmenu:antirepeat:delete",
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔢 Takror soni: {cfg.get('threshold', 3)}",
                callback_data="modmenu:antirepeat:threshold_menu",
            ),
            InlineKeyboardButton(
                f"⏱️ Oyna: {cfg.get('window', 10)}s",
                callback_data="modmenu:antirepeat:window_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                f"⚖️ Jazo: {_antirepeat_action_name(cfg.get('action', 'warn'))}",
                callback_data="modmenu:antirepeat:action_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Ortga",
                callback_data="modpage:1",
            ),
        ],
    ])


def _antirepeat_action_name(action):
    return {
        "warn": "⚠️ Warn",
        "mute": "🔇 Mute",
        "ban": "🚫 Ban",
    }.get(action, "⚠️ Warn")


def _antirepeat_duration_name(value):
    names = {
        "60": "1 daqiqa",
        "300": "5 daqiqa",
        "600": "10 daqiqa",
        "1800": "30 daqiqa",
        "3600": "1 soat",
        "21600": "6 soat",
        "86400": "1 kun",
        "604800": "7 kun",
        "permanent": "♾️ Doimiy",
    }
    return names.get(str(value), str(value))


def _antirepeat_text(cfg):
    return (
        "🔁 <b>Anti-Repeat</b>\n\n"
        f"Holat: {'✅ Yoqilgan' if cfg.get('enabled', False) else '❌ O‘chirilgan'}\n"
        f"🗑️ Avto-o‘chirish: {'✅ Yoqilgan' if cfg.get('delete', True) else '❌ O‘chirilgan'}\n"
        f"🔢 Jazo uchun takror: <b>{cfg.get('threshold', 3)}</b> marta\n"
        f"⏱️ Hisoblash oynasi: <b>{cfg.get('window', 10)}</b> soniya\n"
        f"⚖️ Jazo: <b>{_antirepeat_action_name(cfg.get('action', 'warn'))}</b>\n"
        f"🔇 Mute: <b>{_antirepeat_duration_name(cfg.get('mute_duration', '600'))}</b>"
    )


def _antirepeat_threshold_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("2️⃣", callback_data="modmenu:antirepeat:setthreshold:2"),
            InlineKeyboardButton("3️⃣", callback_data="modmenu:antirepeat:setthreshold:3"),
            InlineKeyboardButton("4️⃣", callback_data="modmenu:antirepeat:setthreshold:4"),
        ],
        [
            InlineKeyboardButton("5️⃣", callback_data="modmenu:antirepeat:setthreshold:5"),
            InlineKeyboardButton("7️⃣", callback_data="modmenu:antirepeat:setthreshold:7"),
            InlineKeyboardButton("🔟", callback_data="modmenu:antirepeat:setthreshold:10"),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modmenu:antirepeat"),
        ],
    ])


def _antirepeat_window_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5s", callback_data="modmenu:antirepeat:setwindow:5"),
            InlineKeyboardButton("10s", callback_data="modmenu:antirepeat:setwindow:10"),
            InlineKeyboardButton("20s", callback_data="modmenu:antirepeat:setwindow:20"),
        ],
        [
            InlineKeyboardButton("30s", callback_data="modmenu:antirepeat:setwindow:30"),
            InlineKeyboardButton("60s", callback_data="modmenu:antirepeat:setwindow:60"),
            InlineKeyboardButton("120s", callback_data="modmenu:antirepeat:setwindow:120"),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modmenu:antirepeat"),
        ],
    ])


def _antirepeat_action_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ Warn", callback_data="modmenu:antirepeat:setaction:warn"),
            InlineKeyboardButton("🔇 Mute", callback_data="modmenu:antirepeat:setaction:mute"),
        ],
        [
            InlineKeyboardButton("🚫 Ban", callback_data="modmenu:antirepeat:setaction:ban"),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modmenu:antirepeat"),
        ],
    ])


def _antirepeat_mute_keyboard():
    values = [
        ("1m", "60"),
        ("5m", "300"),
        ("10m", "600"),
        ("30m", "1800"),
        ("1h", "3600"),
        ("6h", "21600"),
        ("1d", "86400"),
        ("7d", "604800"),
        ("♾️ Doimiy", "permanent"),
    ]
    rows = []
    for i in range(0, len(values), 3):
        rows.append([
            InlineKeyboardButton(
                label,
                callback_data=f"modmenu:antirepeat:setmute:{value}",
            )
            for label, value in values[i:i + 3]
        ])
    rows.append([
        InlineKeyboardButton(
            "🔙 Ortga",
            callback_data="modmenu:antirepeat",
        )
    ])
    return InlineKeyboardMarkup(rows)


def _antirepeat_normalize(text):
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _antirepeat_is_repeatable(message):
    text = message.text or message.caption or ""
    if not text.strip():
        return False
    return True


async def antirepeat_message(update, context):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or chat.type not in ("group", "supergroup"):
        return

    if not user or user.is_bot:
        return

    if message.text and message.text.startswith("/"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _antirepeat_config(mod)

    if not cfg.get("enabled", False):
        return

    if await _is_group_admin(update, context, user.id):
        return

    if not _antirepeat_is_repeatable(message):
        return

    text = _antirepeat_normalize(message.text or message.caption or "")
    if not text:
        return

    runtime = mod.setdefault("_antirepeat_runtime", {})
    uid = str(user.id)
    now = datetime.now(timezone.utc).timestamp()
    window = max(1, min(int(cfg.get("window", 10)), 120))
    threshold = max(2, min(int(cfg.get("threshold", 3)), 10))

    user_items = runtime.setdefault(uid, [])

    user_items[:] = [
        item for item in user_items
        if now - float(item.get("time", 0)) <= window
    ]

    user_items.append({
        "text": text,
        "time": now,
        "message_id": message.message_id,
    })

    same_count = sum(1 for item in user_items if item.get("text") == text)

    if same_count < threshold:
        save_data(data)
        return

    # Jazo ishga tushgach shu xabarlar oynasini tozalaymiz.
    runtime[uid] = []

    if cfg.get("delete", True):
        try:
            await message.delete()
        except TelegramError:
            pass

    violations = cfg.setdefault("violations", {})
    violations[uid] = int(violations.get(uid, 0)) + 1

    action = cfg.get("action", "warn")

    if action == "warn":
        warns = cfg.setdefault("warns", {})
        warns[uid] = int(warns.get(uid, 0)) + 1

        try:
            sent = await context.bot.send_message(
                chat.id,
                f"⚠️ {user.mention_html()} bir xil xabarni "
                f"{same_count} marta takrorlagani uchun ogohlantirildi.",
                parse_mode="HTML",
            )
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                8,
            )
        except Exception:
            pass

    elif action == "mute":
        duration = str(cfg.get("mute_duration", "600"))
        permissions = ChatPermissions(can_send_messages=False)

        try:
            if duration == "permanent":
                await context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=permissions,
                )
            else:
                seconds = max(1, int(duration))
                until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
                await context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=permissions,
                    until_date=until,
                )

            try:
                sent = await context.bot.send_message(
                    chat.id,
                    f"🔇 {user.mention_html()} takroriy xabarlar "
                    f"sababli mute qilindi.\n"
                    f"⏱️ {_antirepeat_duration_name(duration)}",
                    parse_mode="HTML",
                )
                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                    8,
                )
            except Exception:
                pass

        except TelegramError:
            pass

    elif action == "ban":
        try:
            await context.bot.ban_chat_member(chat.id, user.id)

            try:
                sent = await context.bot.send_message(
                    chat.id,
                    f"🚫 {user.mention_html()} takroriy xabarlarni "
                    f"qayta-qayta yuborgani uchun ban qilindi.",
                    parse_mode="HTML",
                )
                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                    8,
                )
            except Exception:
                pass

        except TelegramError:
            pass

    save_data(data)


async def antirepeat_callback(update, context):
    query = update.callback_query
    await query.answer()

    data_cb = query.data
    chat = query.message.chat

    if chat.type not in ("group", "supergroup"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)

    if not await _is_group_admin(update, context, query.from_user.id):
        await query.answer("❌ Siz guruh administratori emassiz.", show_alert=True)
        return

    cfg = _antirepeat_config(mod)

    if data_cb == "modmenu:antirepeat":
        await query.edit_message_text(
            _antirepeat_text(cfg),
            parse_mode="HTML",
            reply_markup=_antirepeat_keyboard(cfg),
        )
        return

    if data_cb == "modmenu:antirepeat:toggle":
        cfg["enabled"] = not cfg.get("enabled", False)

    elif data_cb == "modmenu:antirepeat:delete":
        cfg["delete"] = not cfg.get("delete", True)

    elif data_cb == "modmenu:antirepeat:threshold_menu":
        await query.edit_message_text(
            "🔢 <b>Jazo uchun nechta bir xil xabar kerak?</b>",
            parse_mode="HTML",
            reply_markup=_antirepeat_threshold_keyboard(),
        )
        return

    elif data_cb == "modmenu:antirepeat:window_menu":
        await query.edit_message_text(
            "⏱️ <b>Takrorlarni qaysi vaqt oralig‘ida hisoblaymiz?</b>",
            parse_mode="HTML",
            reply_markup=_antirepeat_window_keyboard(),
        )
        return

    elif data_cb == "modmenu:antirepeat:action_menu":
        await query.edit_message_text(
            "⚖️ <b>Anti-Repeat jazosi:</b>",
            parse_mode="HTML",
            reply_markup=_antirepeat_action_keyboard(),
        )
        return

    elif data_cb.startswith("modmenu:antirepeat:setthreshold:"):
        value = int(data_cb.rsplit(":", 1)[1])
        cfg["threshold"] = max(2, min(value, 10))

    elif data_cb.startswith("modmenu:antirepeat:setwindow:"):
        value = int(data_cb.rsplit(":", 1)[1])
        cfg["window"] = max(1, min(value, 120))

    elif data_cb.startswith("modmenu:antirepeat:setaction:"):
        value = data_cb.rsplit(":", 1)[1]
        if value in ("warn", "mute", "ban"):
            cfg["action"] = value

    elif data_cb.startswith("modmenu:antirepeat:setmute:"):
        value = data_cb.rsplit(":", 1)[1]
        cfg["mute_duration"] = value

    else:
        return

    save_data(data)

    await query.edit_message_text(
        _antirepeat_text(cfg),
        parse_mode="HTML",
        reply_markup=_antirepeat_keyboard(cfg),
    )


# ============================================================
# 🔠 ANTI-CAPS — 11-BOSQICH
# ============================================================

def _anticaps_config(mod):
    cfg = mod.setdefault("anticaps", {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("delete", True)
    cfg.setdefault("percent", 70)
    cfg.setdefault("action", "warn")
    cfg.setdefault("mute_duration", "600")
    cfg.setdefault("violations", {})
    cfg.setdefault("warns", {})
    return cfg


def _anticaps_action_name(action):
    return {
        "warn": "⚠️ Warn",
        "mute": "🔇 Mute",
        "ban": "🚫 Ban",
    }.get(action, "⚠️ Warn")


def _anticaps_duration_name(value):
    names = {
        "60": "1 daqiqa",
        "300": "5 daqiqa",
        "600": "10 daqiqa",
        "1800": "30 daqiqa",
        "3600": "1 soat",
        "21600": "6 soat",
        "86400": "1 kun",
        "604800": "7 kun",
        "permanent": "♾️ Doimiy",
    }
    return names.get(str(value), str(value))


def _anticaps_text(cfg):
    return (
        "🔠 <b>Anti-Caps</b>\n\n"
        f"Holat: {'✅ Yoqilgan' if cfg.get('enabled', False) else '❌ O‘chirilgan'}\n"
        f"🗑️ Avto-o‘chirish: {'✅ Yoqilgan' if cfg.get('delete', True) else '❌ O‘chirilgan'}\n"
        f"📊 Caps chegarasi: <b>{cfg.get('percent', 70)}%</b>\n"
        f"⚖️ Jazo: <b>{_anticaps_action_name(cfg.get('action', 'warn'))}</b>\n"
        f"🔇 Mute: <b>{_anticaps_duration_name(cfg.get('mute_duration', '600'))}</b>"
    )


def _anticaps_keyboard(cfg):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{'✅ Yoqilgan' if cfg.get('enabled', False) else '❌ O‘chirilgan'}",
                callback_data="modmenu:anticaps:toggle",
            ),
        ],
        [
            InlineKeyboardButton(
                f"🗑️ Avto-o‘chirish: {'✅' if cfg.get('delete', True) else '❌'}",
                callback_data="modmenu:anticaps:delete",
            ),
        ],
        [
            InlineKeyboardButton(
                f"📊 Chegara: {cfg.get('percent', 70)}%",
                callback_data="modmenu:anticaps:percent_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                f"⚖️ Jazo: {_anticaps_action_name(cfg.get('action', 'warn'))}",
                callback_data="modmenu:anticaps:action_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔇 Mute: {_anticaps_duration_name(cfg.get('mute_duration', '600'))}",
                callback_data="modmenu:anticaps:mute_menu",
            ),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modpage:1"),
        ],
    ])


def _anticaps_percent_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("50%", callback_data="modmenu:anticaps:setpercent:50"),
            InlineKeyboardButton("60%", callback_data="modmenu:anticaps:setpercent:60"),
            InlineKeyboardButton("70%", callback_data="modmenu:anticaps:setpercent:70"),
        ],
        [
            InlineKeyboardButton("80%", callback_data="modmenu:anticaps:setpercent:80"),
            InlineKeyboardButton("90%", callback_data="modmenu:anticaps:setpercent:90"),
            InlineKeyboardButton("95%", callback_data="modmenu:anticaps:setpercent:95"),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modmenu:anticaps"),
        ],
    ])


def _anticaps_action_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ Warn", callback_data="modmenu:anticaps:setaction:warn"),
            InlineKeyboardButton("🔇 Mute", callback_data="modmenu:anticaps:setaction:mute"),
        ],
        [
            InlineKeyboardButton("🚫 Ban", callback_data="modmenu:anticaps:setaction:ban"),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modmenu:anticaps"),
        ],
    ])


def _anticaps_mute_keyboard():
    values = [
        ("1m", "60"),
        ("5m", "300"),
        ("10m", "600"),
        ("30m", "1800"),
        ("1h", "3600"),
        ("6h", "21600"),
        ("1d", "86400"),
        ("7d", "604800"),
        ("♾️ Doimiy", "permanent"),
    ]

    rows = []
    for i in range(0, len(values), 3):
        rows.append([
            InlineKeyboardButton(
                label,
                callback_data=f"modmenu:anticaps:setmute:{value}",
            )
            for label, value in values[i:i + 3]
        ])

    rows.append([
        InlineKeyboardButton(
            "🔙 Ortga",
            callback_data="modmenu:anticaps",
        )
    ])

    return InlineKeyboardMarkup(rows)


def _anticaps_is_caps(message, percent):
    text = message.text or message.caption or ""

    letters = [char for char in text if char.isalpha()]

    if len(letters) < 5:
        return False

    upper = sum(1 for char in letters if char.isupper())
    ratio = (upper / len(letters)) * 100

    return ratio >= percent


async def anticaps_message(update, context):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or chat.type not in ("group", "supergroup"):
        return

    if not user or user.is_bot:
        return

    if message.text and message.text.startswith("/"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _anticaps_config(mod)

    if not cfg.get("enabled", False):
        return

    if await _is_group_admin(update, context, user.id):
        return

    percent = max(50, min(int(cfg.get("percent", 70)), 100))

    if not _anticaps_is_caps(message, percent):
        return

    if cfg.get("delete", True):
        try:
            await message.delete()
        except TelegramError:
            pass

    uid = str(user.id)

    violations = cfg.setdefault("violations", {})
    violations[uid] = int(violations.get(uid, 0)) + 1

    action = cfg.get("action", "warn")

    if action == "warn":
        warns = cfg.setdefault("warns", {})
        warns[uid] = int(warns.get(uid, 0)) + 1

        try:
            sent = await context.bot.send_message(
                chat.id,
                f"⚠️ {user.mention_html()} xabarida juda ko‘p "
                f"katta harf ishlatilgani uchun ogohlantirildi.",
                parse_mode="HTML",
            )

            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                8,
            )
        except Exception:
            pass

    elif action == "mute":
        duration = str(cfg.get("mute_duration", "600"))
        permissions = ChatPermissions(can_send_messages=False)

        try:
            if duration == "permanent":
                await context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=permissions,
                )
            else:
                seconds = max(1, int(duration))
                until = datetime.now(timezone.utc) + timedelta(seconds=seconds)

                await context.bot.restrict_chat_member(
                    chat.id,
                    user.id,
                    permissions=permissions,
                    until_date=until,
                )

            try:
                sent = await context.bot.send_message(
                    chat.id,
                    f"🔇 {user.mention_html()} Anti-Caps sababli "
                    f"mute qilindi.\n"
                    f"⏱️ {_anticaps_duration_name(duration)}",
                    parse_mode="HTML",
                )

                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                    8,
                )
            except Exception:
                pass

        except TelegramError:
            pass

    elif action == "ban":
        try:
            await context.bot.ban_chat_member(chat.id, user.id)

            try:
                sent = await context.bot.send_message(
                    chat.id,
                    f"🚫 {user.mention_html()} Anti-Caps sababli ban qilindi.",
                    parse_mode="HTML",
                )

                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat.id, sent.message_id),
                    8,
                )
            except Exception:
                pass

        except TelegramError:
            pass

    save_data(data)


async def anticaps_callback(update, context):
    query = update.callback_query

    if not query:
        return

    data_cb = query.data or ""

    await query.answer()

    if not query.message:
        return

    chat = query.message.chat

    if chat.type not in ("group", "supergroup"):
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)

    if not await _is_group_admin(update, context, query.from_user.id):
        await query.answer(
            "❌ Siz guruh administratori emassiz.",
            show_alert=True,
        )
        return

    cfg = _anticaps_config(mod)

    if data_cb == "modmenu:anticaps":
        await query.edit_message_text(
            _anticaps_text(cfg),
            parse_mode="HTML",
            reply_markup=_anticaps_keyboard(cfg),
        )
        return

    if data_cb == "modmenu:anticaps:toggle":
        cfg["enabled"] = not cfg.get("enabled", False)

    elif data_cb == "modmenu:anticaps:delete":
        cfg["delete"] = not cfg.get("delete", True)

    elif data_cb == "modmenu:anticaps:percent_menu":
        await query.edit_message_text(
            "📊 <b>Anti-Caps chegarasini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=_anticaps_percent_keyboard(),
        )
        return

    elif data_cb == "modmenu:anticaps:action_menu":
        await query.edit_message_text(
            "⚖️ <b>Anti-Caps jazosi:</b>",
            parse_mode="HTML",
            reply_markup=_anticaps_action_keyboard(),
        )
        return

    elif data_cb == "modmenu:anticaps:mute_menu":
        await query.edit_message_text(
            "🔇 <b>Mute davomiyligini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=_anticaps_mute_keyboard(),
        )
        return

    elif data_cb.startswith("modmenu:anticaps:setpercent:"):
        value = int(data_cb.rsplit(":", 1)[1])
        cfg["percent"] = max(50, min(value, 100))

    elif data_cb.startswith("modmenu:anticaps:setaction:"):
        value = data_cb.rsplit(":", 1)[1]
        if value in ("warn", "mute", "ban"):
            cfg["action"] = value

    elif data_cb.startswith("modmenu:anticaps:setmute:"):
        cfg["mute_duration"] = data_cb.rsplit(":", 1)[1]

    else:
        return

    save_data(data)

    await query.edit_message_text(
        _anticaps_text(cfg),
        parse_mode="HTML",
        reply_markup=_anticaps_keyboard(cfg),
    )

# ============================================================
# 👥 ANTI-MENTION
# ============================================================

def _antimention_config(mod):
    cfg = mod.setdefault("antimention", {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("delete", True)
    cfg.setdefault("limit", 3)
    cfg.setdefault("action", "warn")
    cfg.setdefault("mute_duration", "600")
    cfg.setdefault("violations", {})
    cfg.setdefault("warns", {})
    return cfg


def _antimention_action_name(action):
    return {
        "warn": "⚠️ Warn",
        "mute": "🔇 Mute",
        "ban": "🚫 Ban",
    }.get(action, "⚠️ Warn")


def _antimention_duration_name(value):
    if str(value) in ("0", "permanent"):
        return "♾️ Doimiy"
    names = {
        "60": "1 daqiqa",
        "300": "5 daqiqa",
        "600": "10 daqiqa",
        "1800": "30 daqiqa",
        "3600": "1 soat",
        "21600": "6 soat",
        "86400": "1 kun",
        "604800": "7 kun",
    }
    return names.get(str(value), str(value))


def _antimention_keyboard(cfg):
    enabled = "✅ Yoqilgan" if cfg.get("enabled") else "❌ O‘chirilgan"
    delete = "✅ Yoqilgan" if cfg.get("delete") else "❌ O‘chirilgan"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                enabled,
                callback_data="modmenu:antimention:toggle",
            ),
            InlineKeyboardButton(
                f"🗑️ O‘chirish: {delete}",
                callback_data="modmenu:antimention:delete",
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔢 Limit: {cfg.get('limit', 3)}",
                callback_data="modmenu:antimention:limit_menu",
            ),
            InlineKeyboardButton(
                f"⚖️ Jazo: {_antimention_action_name(cfg.get('action', 'warn'))}",
                callback_data="modmenu:antimention:action_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                f"⏱️ Mute: {_antimention_duration_name(cfg.get('mute_duration', '600'))}",
                callback_data="modmenu:antimention:mute_menu",
            ),
        ],
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="modpage:1"),
        ],
    ])


def _antimention_limit_keyboard():
    values = [1, 2, 3, 5, 10]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                str(value),
                callback_data=f"modmenu:antimention:setlimit:{value}",
            )
            for value in values
        ],
        [
            InlineKeyboardButton(
                "🔙 Ortga",
                callback_data="modmenu:antimention",
            )
        ],
    ])


def _antimention_action_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚠️ Warn",
                callback_data="modmenu:antimention:setaction:warn",
            ),
            InlineKeyboardButton(
                "🔇 Mute",
                callback_data="modmenu:antimention:setaction:mute",
            ),
        ],
        [
            InlineKeyboardButton(
                "🚫 Ban",
                callback_data="modmenu:antimention:setaction:ban",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Ortga",
                callback_data="modmenu:antimention",
            )
        ],
    ])


def _antimention_mute_keyboard():
    values = [
        ("1m", "60"),
        ("5m", "300"),
        ("10m", "600"),
        ("30m", "1800"),
        ("1h", "3600"),
        ("6h", "21600"),
        ("1d", "86400"),
        ("7d", "604800"),
        ("♾️", "permanent"),
    ]

    rows = []
    row = []

    for label, value in values:
        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"modmenu:antimention:setmute:{value}",
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton(
            "🔙 Ortga",
            callback_data="modmenu:antimention",
        )
    ])

    return InlineKeyboardMarkup(rows)


def _antimention_text(cfg):
    status = "✅ Yoqilgan" if cfg.get("enabled") else "❌ O‘chirilgan"
    delete = "✅ Yoqilgan" if cfg.get("delete") else "❌ O‘chirilgan"

    return (
        "👥 <b>Anti-Mention</b>\n\n"
        f"Holat: {status}\n"
        f"🗑️ Avto-o‘chirish: {delete}\n"
        f"🔢 Mention limiti: {cfg.get('limit', 3)}\n"
        f"⚖️ Jazo: {_antimention_action_name(cfg.get('action', 'warn'))}\n"
        f"⏱️ Mute: {_antimention_duration_name(cfg.get('mute_duration', '600'))}"
    )


def _antimention_count(message):
    count = 0

    entities = list(message.entities or [])
    entities += list(message.caption_entities or [])

    for entity in entities:
        if entity.type in ("mention", "text_mention"):
            count += 1

    text = message.text or message.caption or ""

    # Entity topilmagan oddiy @username holati uchun fallback.
    count += len(re.findall(r"(?<!\w)@[A-Za-z0-9_]{3,}", text))

    return count


async def antimention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    user = query.from_user
    chat = update.effective_chat

    if not chat or chat.type not in ("group", "supergroup"):
        await query.answer("❌ Bu sozlama guruh uchun.", show_alert=True)
        return

    if not await _is_group_admin(update, context, user.id):
        await query.answer("🚫 Faqat adminlar.", show_alert=True)
        return

    data_cb = query.data or ""
    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _antimention_config(mod)

    if data_cb == "modmenu:antimention":
        await query.answer()
        await query.edit_message_text(
            _antimention_text(cfg),
            parse_mode="HTML",
            reply_markup=_antimention_keyboard(cfg),
        )
        save_data(data)
        return

    if data_cb == "modmenu:antimention:toggle":
        cfg["enabled"] = not cfg.get("enabled", False)

    elif data_cb == "modmenu:antimention:delete":
        cfg["delete"] = not cfg.get("delete", True)

    elif data_cb == "modmenu:antimention:limit_menu":
        await query.answer()
        await query.edit_message_text(
            "🔢 <b>Mention limitini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=_antimention_limit_keyboard(),
        )
        return

    elif data_cb == "modmenu:antimention:action_menu":
        await query.answer()
        await query.edit_message_text(
            "⚖️ <b>Jazo turini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=_antimention_action_keyboard(),
        )
        return

    elif data_cb == "modmenu:antimention:mute_menu":
        await query.answer()
        await query.edit_message_text(
            "⏱️ <b>Mute muddatini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=_antimention_mute_keyboard(),
        )
        return

    elif data_cb.startswith("modmenu:antimention:setlimit:"):
        try:
            value = int(data_cb.rsplit(":", 1)[1])
            cfg["limit"] = max(1, min(value, 10))
        except ValueError:
            await query.answer("❌ Noto‘g‘ri limit.", show_alert=True)
            return

    elif data_cb.startswith("modmenu:antimention:setaction:"):
        action = data_cb.rsplit(":", 1)[1]
        if action not in ("warn", "mute", "ban"):
            await query.answer("❌ Noto‘g‘ri jazo.", show_alert=True)
            return
        cfg["action"] = action

    elif data_cb.startswith("modmenu:antimention:setmute:"):
        value = data_cb.rsplit(":", 1)[1]
        allowed = {
            "60", "300", "600", "1800",
            "3600", "21600", "86400",
            "604800", "permanent",
        }
        if value not in allowed:
            await query.answer("❌ Noto‘g‘ri muddat.", show_alert=True)
            return
        cfg["mute_duration"] = value

    else:
        await query.answer()
        return

    save_data(data)
    await query.answer("✅ Saqlandi")
    await query.edit_message_text(
        _antimention_text(cfg),
        parse_mode="HTML",
        reply_markup=_antimention_keyboard(cfg),
    )


async def antimention_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    print(
        f"🔎 AM-1 | message={bool(message)} chat={getattr(chat, 'id', None)} "
        f"user={getattr(user, 'id', None)}",
        flush=True,
    )

    if not message or not chat or chat.type not in ("group", "supergroup"):
        print("⏭️ AM-2 | group emas yoki message yo‘q", flush=True)
        return

    if not user or user.is_bot:
        print("⏭️ AM-3 | user yo‘q yoki bot", flush=True)
        return

    if message.text and message.text.startswith("/"):
        print("⏭️ AM-4 | command", flush=True)
        return

    data = load_data()
    group, mod = _get_moderation_group(data, chat.id)
    cfg = _antimention_config(mod)

    print(
        f"🔎 AM-5 | enabled={cfg.get('enabled')} "
        f"delete={cfg.get('delete')} limit={cfg.get('limit')} "
        f"action={cfg.get('action')} mute={cfg.get('mute_duration')}",
        flush=True,
    )

    if not cfg.get("enabled", False):
        print("⏭️ AM-6 | Anti-Mention o‘chiq", flush=True)
        return

    global_admin = is_admin(user.id)

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        telegram_admin = member.status in ("creator", "administrator")
        print(
            f"🔎 AM-7 | telegram_status={member.status} "
            f"global_admin={global_admin} telegram_admin={telegram_admin}",
            flush=True,
        )
    except TelegramError as e:
        telegram_admin = False
        print(f"⚠️ AM-7 | get_chat_member xatosi: {e!r}", flush=True)

    if global_admin or telegram_admin:
        print("⏭️ AM-8 | admin himoyasi sabab return", flush=True)
        return

    count = _antimention_count(message)
    limit = max(1, min(int(cfg.get("limit", 3)), 10))

    print(
        f"🔎 AM-9 | mention_count={count} limit={limit}",
        flush=True,
    )

    if count < limit:
        print("⏭️ AM-10 | limitga yetmadi", flush=True)
        return

    print("🚨 AM-11 | JAZO SHARTI BAJARILDI", flush=True)

    user_id = str(user.id)

    violations = cfg.setdefault("violations", {})
    violations[user_id] = int(violations.get(user_id, 0)) + 1

    if cfg.get("delete", True):
        try:
            await message.delete()
            print("✅ AM-12 | xabar o‘chirildi", flush=True)
        except TelegramError as e:
            print(f"❌ AM-12 | xabar o‘chmadi: {e!r}", flush=True)

    action = cfg.get("action", "warn")

    try:
        if action == "warn":
            warns = cfg.setdefault("warns", {})
            warns[user_id] = int(warns.get(user_id, 0)) + 1

            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"⚠️ <b>Ogohlantirish!</b>\n"
                    f"👤 Foydalanuvchi: {user.mention_html()}\n"
                    f"👥 Mention limiti: {limit}"
                ),
                parse_mode="HTML",
            )
            print("✅ AM-13 | WARN berildi", flush=True)

        elif action == "mute":
            duration = str(cfg.get("mute_duration", "600"))

            if duration == "permanent":
                until = None
            else:
                seconds = max(60, int(duration))
                until = datetime.now(timezone.utc) + timedelta(seconds=seconds)

            permissions = ChatPermissions(can_send_messages=False)

            print(
                f"🔇 AM-13 | MUTE yuborilmoqda | duration={duration} "
                f"until={until}",
                flush=True,
            )

            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=permissions,
                until_date=until,
            )

            print("✅ AM-14 | MUTE berildi", flush=True)

            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"🔇 <b>Mute!</b>\n"
                    f"👤 {user.mention_html()}\n"
                    f"⏱️ Muddat: {duration}"
                ),
                parse_mode="HTML",
            )

        elif action == "ban":
            print("🚫 AM-13 | BAN yuborilmoqda", flush=True)

            await context.bot.ban_chat_member(
                chat_id=chat.id,
                user_id=user.id,
            )

            print("✅ AM-14 | BAN berildi", flush=True)

            await context.bot.send_message(
                chat_id=chat.id,
                text=f"🚫 <b>Ban!</b>\n👤 {user.mention_html()}",
                parse_mode="HTML",
            )

        else:
            print(f"⚠️ AM-13 | Noma’lum action: {action!r}", flush=True)

    except TelegramError as e:
        print(
            f"❌ AM-ERROR | Telegram xatosi | "
            f"chat={chat.id} user={user.id} action={action} | {e!r}",
            flush=True,
        )
    except Exception as e:
        print(
            f"❌ AM-ERROR | Kutilmagan xato | "
            f"chat={chat.id} user={user.id} action={action} | {e!r}",
            flush=True,
        )

    save_data(data)
    print("💾 AM-15 | data saqlandi", flush=True)
