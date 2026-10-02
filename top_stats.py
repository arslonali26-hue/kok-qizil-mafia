from datetime import datetime, timedelta, timezone
from database import load_data


def _now():
    return datetime.now(timezone.utc)


def _today_key():
    return _now().strftime("%Y-%m-%d")


def _period_days(days):
    if days is None:
        return None

    end = _now()
    start = end - timedelta(days=days)

    return start, end


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _user_stats(user):
    return {
        "wins": _safe_int(user.get("battle_wins", user.get("wins", 0))),
        "losses": _safe_int(user.get("battle_losses", user.get("losses", 0))),
        "battles": _safe_int(user.get("battles", 0)),
        "attacks": _safe_int(user.get("attacks", 0)),
        "damage": _safe_int(
            user.get("damage_dealt", user.get("battle_damage", 0))
        ),
        "kills": _safe_int(
            user.get("kills", user.get("battle_kills", 0))
        ),
        "defenses": _safe_int(user.get("defenses_used", 0)),
        "medkits": _safe_int(user.get("medkits_used", 0)),
        "streak": _safe_int(user.get("win_streak", 0)),
        "pul": _safe_int(user.get("pul_earned", 0)),
        "almas": _safe_int(user.get("almas_earned", 0)),
        "weapon_xp": _safe_int(user.get("weapon_xp_earned", 0)),
    }


def _history_user_stats(history, user_id, days):
    if not isinstance(history, dict):
        return None

    now = _now()

    # 📅 Kalendar bo‘yicha davr:
    # 1 = bugun, 7 = bugun + oldingi 6 kun, 30 = bugun + oldingi 29 kun.
    if days == 1:
        start = datetime(
            now.year,
            now.month,
            now.day,
            tzinfo=timezone.utc,
        )
    else:
        start = datetime(
            now.year,
            now.month,
            now.day,
            tzinfo=timezone.utc,
        ) - timedelta(days=max(0, days - 1))

    result = {
        "wins": 0,
        "losses": 0,
        "battles": 0,
        "attacks": 0,
        "damage": 0,
        "kills": 0,
        "defenses": 0,
        "medkits": 0,
        "pul": 0,
        "almas": 0,
        "weapon_xp": 0,
    }

    found = False

    for date_key, bucket in history.items():
        try:
            day = datetime.strptime(
                str(date_key), "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue

        if day < start:
            continue

        if not isinstance(bucket, dict):
            continue

        users = bucket.get("users", {})
        if not isinstance(users, dict):
            continue

        item = users.get(str(user_id))
        if not isinstance(item, dict):
            continue

        found = True

        for key in result:
            result[key] += _safe_int(item.get(key, 0))

    return result if found else None


def _merge_period_stats(user, history, user_id, days):
    current = _user_stats(user)

    if days is None:
        return current

    historical = _global_history_user_stats(history, user_id, days)

    # 📅 Vaqtli TOPda tarix bo‘lmasa, all-time statistikani
    # noto‘g‘ri ko‘rsatmaymiz.
    if historical is None:
        return {
            "wins": 0,
            "losses": 0,
            "battles": 0,
            "attacks": 0,
            "damage": 0,
            "kills": 0,
            "defenses": 0,
            "medkits": 0,
            "streak": current["streak"],
            "pul": 0,
            "almas": 0,
            "weapon_xp": 0,
        }

    historical["streak"] = current["streak"]
    return historical



def _global_history_user_stats(history, user_id, days):
    """🌍 Global TOP uchun barcha guruhlar tarixini birlashtiradi."""
    if not isinstance(history, dict):
        return None

    now = _now()
    if days == 1:
        start = datetime(
            now.year,
            now.month,
            now.day,
            tzinfo=timezone.utc,
        )
    else:
        start = datetime(
            now.year,
            now.month,
            now.day,
            tzinfo=timezone.utc,
        ) - timedelta(days=max(0, days - 1))

    result = {
        "wins": 0,
        "losses": 0,
        "battles": 0,
        "attacks": 0,
        "damage": 0,
        "kills": 0,
        "defenses": 0,
        "medkits": 0,
        "pul": 0,
        "almas": 0,
        "weapon_xp": 0,
    }

    found = False
    uid = str(user_id)

    for date_key, bucket in history.items():
        try:
            day = datetime.strptime(
                str(date_key),
                "%Y-%m-%d",
            ).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue

        if day < start or not isinstance(bucket, dict):
            continue

        # Eski/top-level global tarix
        users = bucket.get("users", {})
        if isinstance(users, dict):
            item = users.get(uid)
            if isinstance(item, dict):
                found = True
                for key in result:
                    result[key] += _safe_int(item.get(key, 0))

        # 10.3 guruh tarixlari — barcha guruhlarni birlashtirish
        groups = bucket.get("groups", {})
        if isinstance(groups, dict):
            for group in groups.values():
                if not isinstance(group, dict):
                    continue

                group_users = group.get("users", {})
                if not isinstance(group_users, dict):
                    continue

                item = group_users.get(uid)
                if not isinstance(item, dict):
                    continue

                found = True
                for key in result:
                    result[key] += _safe_int(item.get(key, 0))

    return result if found else None


def player_top(limit=30, days=None):
    data = load_data()
    users = data.get("users", {})
    history = data.get("stats_history", {})

    result = []

    for uid, user in users.items():
        if not isinstance(user, dict):
            continue

        stats = _merge_period_stats(
            user,
            history,
            uid,
            days,
        )

        result.append({
            "user_id": uid,
            "name": user.get("name")
                or user.get("first_name")
                or f"O‘yinchi {uid}",
            **stats,
        })

    result.sort(
        key=lambda x: (
            -x["wins"],
            -x["damage"],
            -x["battles"],
            -x["kills"],
            str(x["user_id"]),
        )
    )

    return result[:max(1, min(int(limit), 100))]


def _group_stats(group):
    return {
        "battles": _safe_int(group.get("battles", 0)),
        "players": _safe_int(group.get("players", 0)),
        "damage": _safe_int(group.get("damage", 0)),
        "wins": _safe_int(group.get("wins", 0)),
        "defenses": _safe_int(group.get("defenses", 0)),
        "medkits": _safe_int(group.get("medkits", 0)),
    }


def group_top(limit=30, days=None):
    data = load_data()
    groups = data.get("groups", {})

    result = []

    for gid, group in groups.items():
        if not isinstance(group, dict):
            continue

        stats = _group_stats(group)

        if days is not None:
            activity = group.get("activity", {})
            period = 0

            if isinstance(activity, dict):
                now = _now()
                start = now - timedelta(days=days)

                for date_key, value in activity.items():
                    try:
                        day = datetime.strptime(
                            str(date_key),
                            "%Y-%m-%d",
                        ).replace(tzinfo=timezone.utc)
                    except (TypeError, ValueError):
                        continue

                    if day >= start:
                        period += _safe_int(value)

            if period <= 0:
                continue

        result.append({
            "chat_id": gid,
            "title": group.get("title") or "Noma’lum guruh",
            **stats,
        })

    result.sort(
        key=lambda x: (
            -x["battles"],
            -x["damage"],
            -x["wins"],
            str(x["chat_id"]),
        )
    )

    return result[:max(1, min(int(limit), 30))]


def format_player_top(rows, period_name="ALL", start_rank=1):
    lines = [
        f"🏆 O‘YINCHI TOP — {period_name}",
        "━━━━━━━━━━━━━━━━",
    ]

    if not rows:
        lines.append("📭 Hozircha statistika yo‘q.")
        return "\n".join(lines)

    medals = ["🥇", "🥈", "🥉"]

    for offset, item in enumerate(rows):
        index = start_rank + offset
        medal = medals[index - 1] if index <= 3 else f"🏅 {index}."

        lines.append(
            f"{medal} 👤 {item['name']}"
        )
        lines.append(
            f"🏵️ {item['wins']} g‘alaba  ·  "
            f"🗡️ {item['battles']} jang  ·  "
            f"🧨 {item['damage']:,} zarar"
        )
        lines.append(
            f"😿 {item['losses']} mag‘lubiyat  ·  "
            f"🧱 {item['defenses']} himoya  ·  "
            f"🧴 {item['medkits']} aptechka"
        )
        lines.append(
            f"⚡ {item['streak']} ketma-ket  ·  "
            f"🪙 +{item['pul']} Pul  ·  "
            f"🔷 +{item['almas']} Almas"
        )

    return "\n".join(lines)


def format_group_top(rows, period_name="ALL"):
    lines = [
        f"🏆 GURUH TOP — {period_name}",
        "━━━━━━━━━━━━━━━━",
    ]

    if not rows:
        lines.append("📭 Hozircha guruh statistikasi yo‘q.")
        return "\n".join(lines)

    medals = ["🥇", "🥈", "🥉"]

    for index, item in enumerate(rows, 1):
        medal = medals[index - 1] if index <= 3 else f"🏅 {index}."

        lines.append(
            f"{medal} 👥 {item['title']}"
        )
        lines.append(
            f"🗡️ {item['battles']} jang  ·  "
            f"🧑‍🤝‍🧑 {item['players']} o‘yinchi  ·  "
            f"🧨 {item['damage']:,} zarar"
        )
        lines.append(
            f"🏵️ {item['wins']} g‘alaba  ·  "
            f"🧱 {item['defenses']} himoya  ·  "
            f"🧴 {item['medkits']} aptechka"
        )

    return "\n".join(lines)


# ============================================================
# 📊 TOP STATISTIKASINI YOZISH FUNKSIYALARI
# ============================================================

def _history_bucket(data, date_key):
    history = data.setdefault("stats_history", {})
    bucket = history.setdefault(date_key, {})
    bucket.setdefault("users", {})
    bucket.setdefault("groups", {})
    return bucket


def _history_user(bucket, user_id):
    users = bucket.setdefault("users", {})
    uid = str(user_id)

    user = users.setdefault(uid, {})

    fields = (
        "wins",
        "losses",
        "battles",
        "attacks",
        "damage",
        "kills",
        "defenses",
        "medkits",
        "pul",
        "almas",
        "weapon_xp",
    )

    for field in fields:
        user.setdefault(field, 0)

    return user


def _history_group(bucket, chat_id):
    groups = bucket.setdefault("groups", {})
    gid = str(chat_id)

    group = groups.setdefault(gid, {})

    fields = (
        "battles",
        "players",
        "damage",
        "wins",
        "defenses",
        "medkits",
    )

    for field in fields:
        group.setdefault(field, 0)

    return group


def record_user_stat(
    user_id,
    *,
    stat,
    amount=1,
    chat_id=None,
):
    """
    👤 Bitta foydalanuvchining statistik hodisasini
    umumiy statistikaga va kunlik tarixga yozadi.
    """

    data = load_data()
    uid = str(user_id)

    user = data.setdefault("users", {}).setdefault(uid, {})

    if stat not in (
        "wins",
        "losses",
        "battles",
        "attacks",
        "damage",
        "kills",
        "defenses",
        "medkits",
        "pul",
        "almas",
        "weapon_xp",
    ):
        return False

    value = _safe_int(amount)

    # ♾️ All-time
    field_map = {
        "wins": "battle_wins",
        "losses": "battle_losses",
        "battles": "battles",
        "attacks": "attacks",
        "damage": "damage_dealt",
        "kills": "kills",
        "defenses": "defenses_used",
        "medkits": "medkits_used",
        "pul": "pul_earned",
        "almas": "almas_earned",
        "weapon_xp": "weapon_xp_earned",
    }

    field = field_map[stat]
    user[field] = _safe_int(user.get(field, 0)) + value

    user["last_activity"] = _now().isoformat()

    # 🗓️ Buglik tarix
    bucket = _history_bucket(data, _today_key())
    daily_user = _history_user(bucket, uid)
    daily_user[stat] += value

    # 👥 Guruh faoliyati
    if chat_id is not None:
        gid = str(chat_id)

        groups = data.setdefault("groups", {})
        group = groups.setdefault(
            gid,
            {
                "chat_id": _safe_int(chat_id, chat_id),
                "title": "Noma’lum guruh",
                "first_seen": _now().isoformat(),
                "last_seen": _now().isoformat(),
                "battles": 0,
                "players": 0,
                "damage": 0,
                "wins": 0,
                "defenses": 0,
                "medkits": 0,
                "activity": {},
            },
        )

        group["last_seen"] = _now().isoformat()

        activity = group.setdefault("activity", {})
        day = _today_key()

        # Bir hodisa = 1 faoliyat
        activity[day] = _safe_int(activity.get(day, 0)) + 1

        daily_group = _history_group(bucket, gid)

        if stat == "damage":
            daily_group["damage"] += value
        elif stat == "wins":
            daily_group["wins"] += value
        elif stat == "defenses":
            daily_group["defenses"] += value
        elif stat == "medkits":
            daily_group["medkits"] += value
        elif stat == "battles":
            daily_group["battles"] += value

    data["users"][uid] = user

    # 💾 Bitta joyda saqlash
    from database import save_data
    save_data(data)

    return True


def record_battle_start(chat_id, player_ids):
    """
    ⚔️ Jang boshlanganini guruh va o‘yinchilar tarixiga yozadi.
    """

    data = load_data()
    gid = str(chat_id)
    now = _now().isoformat()
    day = _today_key()

    groups = data.setdefault("groups", {})

    group = groups.setdefault(
        gid,
        {
            "chat_id": _safe_int(chat_id, chat_id),
            "title": "Noma’lum guruh",
            "first_seen": now,
            "last_seen": now,
            "battles": 0,
            "players": 0,
            "damage": 0,
            "wins": 0,
            "defenses": 0,
            "medkits": 0,
            "activity": {},
        },
    )

    group["last_seen"] = now
    group["battles"] = _safe_int(group.get("battles", 0)) + 1

    unique_players = set(str(x) for x in (player_ids or []))
    group["players"] = max(
        _safe_int(group.get("players", 0)),
        len(unique_players),
    )

    activity = group.setdefault("activity", {})
    activity[day] = _safe_int(activity.get(day, 0)) + 1

    bucket = _history_bucket(data, day)

    daily_group = _history_group(bucket, gid)
    daily_group["battles"] += 1
    daily_group["players"] = max(
        _safe_int(daily_group.get("players", 0)),
        len(unique_players),
    )

    for uid in unique_players:
        user = data.setdefault("users", {}).setdefault(uid, {})
        user["battles"] = _safe_int(user.get("battles", 0)) + 1
        user["last_activity"] = now

        daily_user = _history_user(bucket, uid)
        daily_user["battles"] += 1

    save_data(data)
    return True


def record_attack(
    attacker_id,
    *,
    damage=0,
    killed=False,
    chat_id=None,
):
    """
    🗡️ Bitta hujumni TOP statistikalariga yozadi.
    Bitta save bilan ishlaydi.
    """

    data = load_data()
    uid = str(attacker_id)

    users = data.setdefault("users", {})
    user = users.setdefault(uid, {})

    now = _now()
    day = now.strftime("%Y-%m-%d")

    damage = max(0, _safe_int(damage))

    # 👤 All-time
    user["attacks"] = _safe_int(user.get("attacks", 0)) + 1
    user["damage_dealt"] = (
        _safe_int(user.get("damage_dealt", 0)) + damage
    )

    if killed:
        user["kills"] = _safe_int(user.get("kills", 0)) + 1

    user["last_activity"] = now.isoformat()

    # 🗓️ Kunlik tarix
    bucket = _history_bucket(data, day)
    daily_user = _history_user(bucket, uid)

    daily_user["attacks"] += 1
    daily_user["damage"] += damage

    if killed:
        daily_user["kills"] += 1

    # 👥 Guruh
    if chat_id is not None:
        gid = str(chat_id)
        groups = data.setdefault("groups", {})

        group = groups.setdefault(
            gid,
            {
                "chat_id": _safe_int(chat_id, chat_id),
                "title": "Noma’lum guruh",
                "first_seen": now.isoformat(),
                "last_seen": now.isoformat(),
                "battles": 0,
                "players": 0,
                "damage": 0,
                "wins": 0,
                "defenses": 0,
                "medkits": 0,
                "activity": {},
            },
        )

        group["last_seen"] = now.isoformat()
        group["damage"] = (
            _safe_int(group.get("damage", 0)) + damage
        )

        activity = group.setdefault("activity", {})
        activity[day] = _safe_int(activity.get(day, 0)) + 1

        daily_group = _history_group(bucket, gid)
        daily_group["damage"] += damage

    save_data(data)
    return True

# ============================================================
# 🔟 10.1 — GURUH TOP SAQLASH QATLAMI
# ============================================================

# ============================================================
# 🔟 10.1 — GURUH TOP SAQLASH QATLAMI
# ============================================================

def top10_1_safe_int(value, default=0):
    """🔢 TOP uchun xavfsiz integer."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def top10_1_group(data, chat_id, title=None):
    """👥 Guruh TOP ma'lumotlarini xavfsiz tayyorlaydi."""
    groups = data.setdefault("groups", {})
    gid = str(chat_id)

    group = groups.setdefault(
        gid,
        {
            "chat_id": chat_id,
            "title": "Noma’lum guruh",
            "first_seen": None,
            "last_seen": None,
            "battles": 0,
            "players": 0,
            "damage": 0,
            "wins": 0,
            "defenses": 0,
            "medkits": 0,
            "player_ids": [],
            "activity": {},
        },
    )

    if not isinstance(group, dict):
        group = {
            "chat_id": chat_id,
            "title": "Noma’lum guruh",
            "first_seen": None,
            "last_seen": None,
            "battles": 0,
            "players": 0,
            "damage": 0,
            "wins": 0,
            "defenses": 0,
            "medkits": 0,
            "player_ids": [],
            "activity": {},
        }
        groups[gid] = group

    group.setdefault("chat_id", chat_id)
    group.setdefault("title", "Noma’lum guruh")
    group.setdefault("first_seen", None)
    group.setdefault("last_seen", None)
    group.setdefault("battles", 0)
    group.setdefault("players", 0)
    group.setdefault("damage", 0)
    group.setdefault("wins", 0)
    group.setdefault("defenses", 0)
    group.setdefault("medkits", 0)
    group.setdefault("player_ids", [])
    group.setdefault("activity", {})

    if title:
        group["title"] = str(title)

    return group


def top10_1_history_day(data, date_key):
    """📅 Kunlik TOP tarixini xavfsiz tayyorlaydi."""
    history = data.setdefault("stats_history", {})

    bucket = history.setdefault(
        str(date_key),
        {},
    )

    if not isinstance(bucket, dict):
        bucket = {}
        history[str(date_key)] = bucket

    bucket.setdefault("users", {})
    bucket.setdefault("groups", {})

    return bucket


def top10_1_group_history(
    data,
    date_key,
    chat_id,
    title=None,
):
    """📊 Muayyan guruhning kunlik tarixini tayyorlaydi."""
    bucket = top10_1_history_day(
        data,
        date_key,
    )

    groups = bucket.setdefault(
        "groups",
        {},
    )

    gid = str(chat_id)

    group = groups.setdefault(
        gid,
        {
            "chat_id": chat_id,
            "title": title or "Noma’lum guruh",
            "battles": 0,
            "players": 0,
            "damage": 0,
            "wins": 0,
            "defenses": 0,
            "medkits": 0,
            "player_ids": [],
            "users": {},
        },
    )

    if not isinstance(group, dict):
        group = {
            "chat_id": chat_id,
            "title": title or "Noma’lum guruh",
            "battles": 0,
            "players": 0,
            "damage": 0,
            "wins": 0,
            "defenses": 0,
            "medkits": 0,
            "player_ids": [],
            "users": {},
        }
        groups[gid] = group

    group.setdefault("chat_id", chat_id)
    group.setdefault(
        "title",
        title or "Noma’lum guruh",
    )
    group.setdefault("battles", 0)
    group.setdefault("players", 0)
    group.setdefault("damage", 0)
    group.setdefault("wins", 0)
    group.setdefault("defenses", 0)
    group.setdefault("medkits", 0)
    group.setdefault("player_ids", [])
    group.setdefault("users", {})

    if title:
        group["title"] = str(title)

    return group


def top10_1_register_battle(
    data,
    chat_id,
    player_ids,
    title=None,
    date_key=None,
):
    """⚔️ Jangni guruh TOP tarixiga qayd qiladi."""

    from datetime import datetime, timezone

    if date_key is None:
        date_key = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

    group = top10_1_group(
        data,
        chat_id,
        title,
    )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    if not group.get("first_seen"):
        group["first_seen"] = now

    group["last_seen"] = now

    group["battles"] = (
        top10_1_safe_int(
            group.get("battles", 0)
        ) + 1
    )

    unique_players = {
        str(uid)
        for uid in (player_ids or [])
    }

    old_players = {
        str(uid)
        for uid in group.get(
            "player_ids",
            [],
        )
    }

    old_players.update(
        unique_players
    )

    group["player_ids"] = sorted(
        old_players
    )

    group["players"] = len(
        old_players
    )

    activity = group.setdefault(
        "activity",
        {},
    )

    activity[str(date_key)] = (
        top10_1_safe_int(
            activity.get(
                str(date_key),
                0,
            )
        ) + 1
    )

    daily = top10_1_group_history(
        data,
        date_key,
        chat_id,
        title,
    )

    daily["battles"] = (
        top10_1_safe_int(
            daily.get("battles", 0)
        ) + 1
    )

    daily_ids = {
        str(uid)
        for uid in daily.get(
            "player_ids",
            [],
        )
    }

    daily_ids.update(
        unique_players
    )

    daily["player_ids"] = sorted(
        daily_ids
    )

    daily["players"] = len(
        daily_ids
    )

    return group, daily


def top10_1_register_group_player(
    data,
    chat_id,
    user_id,
    stat,
    amount=1,
    date_key=None,
):
    """👤 Guruh ichidagi bitta o‘yinchi statistikasini yozadi."""

    from datetime import datetime, timezone

    if date_key is None:
        date_key = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

    value = top10_1_safe_int(
        amount
    )

    daily = top10_1_group_history(
        data,
        date_key,
        chat_id,
    )

    users = daily.setdefault(
        "users",
        {},
    )

    uid = str(user_id)

    user = users.setdefault(
        uid,
        {
            "wins": 0,
            "losses": 0,
            "battles": 0,
            "attacks": 0,
            "damage": 0,
            "kills": 0,
            "defenses": 0,
            "medkits": 0,
            "pul": 0,
            "almas": 0,
            "weapon_xp": 0,
        },
    )

    if not isinstance(user, dict):
        user = {}
        users[uid] = user

    for key in (
        "wins",
        "losses",
        "battles",
        "attacks",
        "damage",
        "kills",
        "defenses",
        "medkits",
        "pul",
        "almas",
        "weapon_xp",
    ):
        user.setdefault(key, 0)

    if stat not in user:
        return False

    user[stat] = (
        top10_1_safe_int(
            user.get(stat, 0)
        ) + value
    )

    player_ids = daily.setdefault(
        "player_ids",
        [],
    )

    if uid not in player_ids:
        player_ids.append(uid)

    daily["players"] = len(
        player_ids
    )

    return True



def group_player_top(data, chat_id, limit=30, days=None):
    """👥 Faqat bitta guruhdagi o'yinchilar TOPi."""

    from datetime import datetime, timedelta, timezone

    gid = str(chat_id)
    history = data.get("stats_history", {})

    totals = {}

    if days is None:
        # ALL: barcha kunlarni yig'amiz
        date_items = history.items()
    else:
        now = datetime.now(timezone.utc)
        start = datetime(
            now.year,
            now.month,
            now.day,
            tzinfo=timezone.utc,
        ) - timedelta(days=max(0, days - 1))

        date_items = []

        for date_key, bucket in history.items():
            try:
                day = datetime.strptime(
                    str(date_key),
                    "%Y-%m-%d",
                ).replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue

            if day >= start:
                date_items.append((date_key, bucket))

    for date_key, bucket in date_items:
        if not isinstance(bucket, dict):
            continue

        groups = bucket.get("groups", {})
        if not isinstance(groups, dict):
            continue

        group = groups.get(gid)
        if not isinstance(group, dict):
            continue

        users = group.get("users", {})
        if not isinstance(users, dict):
            continue

        for uid, item in users.items():
            if not isinstance(item, dict):
                continue

            uid = str(uid)

            target = totals.setdefault(
                uid,
                {
                    "wins": 0,
                    "losses": 0,
                    "battles": 0,
                    "attacks": 0,
                    "damage": 0,
                    "kills": 0,
                    "defenses": 0,
                    "medkits": 0,
                    "pul": 0,
                    "almas": 0,
                    "weapon_xp": 0,
                },
            )

            for key in target:
                target[key] += _safe_int(
                    item.get(key, 0)
                )

    # 👤 Foydalanuvchi nomlarini asosiy users bazasidan olamiz.
    users_data = data.get("users", {})

    result = []

    for uid, stats in totals.items():
        user = users_data.get(str(uid), {})

        if not isinstance(user, dict):
            user = {}

        result.append(
            {
                "user_id": str(uid),
                "name": (
                    user.get("name")
                    or user.get("first_name")
                    or f"O‘yinchi {uid}"
                ),
                **stats,
            }
        )

    result.sort(
        key=lambda x: (
            -x["wins"],
            -x["damage"],
            -x["battles"],
            -x["kills"],
            str(x["user_id"]),
        )
    )

    return result[:max(1, min(int(limit), 30))]


def format_group_player_top(
    rows,
    period_name="ALL",
):
    """👥 Guruh o'yinchilari TOP matni."""

    lines = [
        f"🏆 GURUH O‘YINCHILARI TOP — {period_name}",
        "━━━━━━━━━━━━━━━━",
    ]

    if not rows:
        lines.append(
            "📭 Bu guruhda hali statistika yo‘q."
        )
        return "\n".join(lines)

    medals = ["🥇", "🥈", "🥉"]

    for index, item in enumerate(rows, 1):
        medal = (
            medals[index - 1]
            if index <= 3
            else f"🏅 {index}."
        )

        lines.append(
            f"{medal} 👤 {item['name']}"
        )

        lines.append(
            f"🏵️ {item['wins']} g‘alaba  ·  "
            f"🗡️ {item['battles']} jang  ·  "
            f"🧨 {item['damage']:,} zarar"
        )

        lines.append(
            f"😿 {item['losses']} mag‘lubiyat  ·  "
            f"🧱 {item['defenses']} himoya  ·  "
            f"🧴 {item['medkits']} aptechka"
        )

    return "\n".join(lines)


def top10_1_group_summary(
    data,
    chat_id,
):
    """📋 Guruhning hozirgi umumiy TOP ma'lumotlari."""
    group = top10_1_group(
        data,
        chat_id,
    )

    return {
        "chat_id": str(chat_id),
        "title": group.get(
            "title",
            "Noma’lum guruh",
        ),
        "battles": top10_1_safe_int(
            group.get("battles", 0)
        ),
        "players": top10_1_safe_int(
            group.get("players", 0)
        ),
        "damage": top10_1_safe_int(
            group.get("damage", 0)
        ),
        "wins": top10_1_safe_int(
            group.get("wins", 0)
        ),
        "defenses": top10_1_safe_int(
            group.get("defenses", 0)
        ),
        "medkits": top10_1_safe_int(
            group.get("medkits", 0)
        ),
        "last_seen": group.get(
            "last_seen"
        ),
    }


# 🔟 10.2 — GURUHLAR RO‘YXATI

def all_groups(limit=100):
    """
    📋 Bot ishlagan guruhlarni qaytaradi.
    """
    data = load_data()
    groups = data.get("groups", {})

    if not isinstance(groups, dict):
        return []

    result = []

    for gid, group in groups.items():
        if not isinstance(group, dict):
            continue

        result.append({
            "chat_id": group.get(
                "chat_id",
                _safe_int(gid, gid),
            ),
            "title": (
                group.get("title")
                or "Noma’lum guruh"
            ),
            "first_seen": group.get(
                "first_seen"
            ),
            "last_seen": group.get(
                "last_seen"
            ),
            "battles": _safe_int(
                group.get("battles", 0)
            ),
            "players": _safe_int(
                group.get("players", 0)
            ),
            "damage": _safe_int(
                group.get("damage", 0)
            ),
            "wins": _safe_int(
                group.get("wins", 0)
            ),
            "defenses": _safe_int(
                group.get("defenses", 0)
            ),
            "medkits": _safe_int(
                group.get("medkits", 0)
            ),
        })

    result.sort(
        key=lambda x: (
            -x["battles"],
            -x["damage"],
            -x["wins"],
            str(x["chat_id"]),
        )
    )

    limit = max(1, min(int(limit), 100))
    return result[:limit]


def format_groups(rows):
    """
    📋 Bot ishlagan guruhlar ro‘yxatini chiroyli chiqaradi.
    """
    lines = [
        "📋 BOT ISHLAGAN GURUHLAR",
        "━━━━━━━━━━━━━━━━",
    ]

    if not rows:
        lines.append(
            "📭 Hozircha guruh statistikasi yo‘q."
        )
        return "\n".join(lines)

    for index, item in enumerate(rows, 1):
        title = item.get(
            "title"
        ) or "Noma’lum guruh"

        lines.append(
            f"👥 {index}. {title}"
        )
        lines.append(
            f"🆔 ID: {item.get('chat_id')}"
        )
        lines.append(
            f"⚔️ Janglar: {item.get('battles', 0)}"
        )
        lines.append(
            f"🧑‍🤝‍🧑 O‘yinchilar: {item.get('players', 0)}"
        )
        lines.append(
            f"💥 Zarar: {item.get('damage', 0):,}"
        )
        lines.append(
            f"🏆 G‘alabalar: {item.get('wins', 0)}"
        )
        lines.append(
            f"🛡️ Himoyalar: {item.get('defenses', 0)}"
        )
        lines.append(
            f"🩹 Aptechkalar: {item.get('medkits', 0)}"
        )
        lines.append("")

    return "\n".join(lines).rstrip()


# 🔟 10.3 — STATISTIKA ULASH QATLAMI

def top10_3_record_group_event(
    data,
    chat_id,
    user_id,
    stat,
    amount=1,
    title=None,
    date_key=None,
):
    """📊 10.3: jang voqealarini guruh va kunlik TOP tarixiga yozadi."""

    allowed = {
        "wins",
        "losses",
        "battles",
        "attacks",
        "damage",
        "kills",
        "defenses",
        "medkits",
        "pul",
        "almas",
        "weapon_xp",
    }

    if stat not in allowed:
        return False

    value = max(0, top10_1_safe_int(amount))

    if date_key is None:
        date_key = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

    # 👤 O‘yinchi kunlik statistikasi
    ok = top10_1_register_group_player(
        data,
        chat_id,
        user_id,
        stat,
        value,
        date_key=date_key,
    )

    if not ok:
        return False

    # 👥 Guruh umumiy statistikasi
    group = top10_1_group(
        data,
        chat_id,
        title,
    )

    daily = top10_1_group_history(
        data,
        date_key,
        chat_id,
        title,
    )

    group_field_map = {
        "battles": "battles",
        "damage": "damage",
        "wins": "wins",
        "defenses": "defenses",
        "medkits": "medkits",
    }

    field = group_field_map.get(stat)

    if field:
        group[field] = (
            top10_1_safe_int(
                group.get(field, 0)
            ) + value
        )

        daily[field] = (
            top10_1_safe_int(
                daily.get(field, 0)
            ) + value
        )

    group["last_seen"] = datetime.now(
        timezone.utc
    ).isoformat()

    return True
