from database import load_data


def _users():
    data = load_data()
    return data.get("users", {})


def _sorted_users(field):
    users = _users()

    result = []

    for uid, user in users.items():
        if not isinstance(user, dict):
            continue

        try:
            value = int(user.get(field, 0))
        except (TypeError, ValueError):
            value = 0

        result.append({
            "user_id": uid,
            "value": value,
        })

    result.sort(key=lambda x: (-x["value"], int(x["user_id"])))
    return result


def top_wins(limit=10):
    return _sorted_users("battle_wins")[:max(1, int(limit))]


def top_damage(limit=10):
    return _sorted_users("battle_damage")[:max(1, int(limit))]


def top_streak(limit=10):
    return _sorted_users("win_streak")[:max(1, int(limit))]


def ranking_text(limit=10):
    limit = max(1, min(int(limit), 50))

    lines = [
        "🏆 REYTING",
        "━━━━━━━━━━━━━━",
        "",
        "🏆 G‘ALABALAR",
    ]

    for index, item in enumerate(top_wins(limit), 1):
        lines.append(
            f"{index}. 👤 {item['user_id']} — "
            f"{item['value']} g‘alaba"
        )

    lines.extend([
        "",
        "💥 DAMAGE",
    ])

    for index, item in enumerate(top_damage(limit), 1):
        lines.append(
            f"{index}. 👤 {item['user_id']} — "
            f"{item['value']} damage"
        )

    lines.extend([
        "",
        "🔥 WIN STREAK",
    ])

    for index, item in enumerate(top_streak(limit), 1):
        lines.append(
            f"{index}. 👤 {item['user_id']} — "
            f"{item['value']} streak"
        )

    return "\n".join(lines)
