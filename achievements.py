from database import load_data, save_data


ACHIEVEMENTS = {
    "first_win": {
        "name": "🥇 Birinchi g‘alaba",
        "description": "Birinchi jangda g‘alaba qozoning.",
        "reward_pul": 50,
        "reward_almas": 0,
    },
    "five_wins": {
        "name": "🏆 5 g‘alaba",
        "description": "Jami 5 ta g‘alabaga erishing.",
        "reward_pul": 100,
        "reward_almas": 0,
    },
    "ten_wins": {
        "name": "👑 10 g‘alaba",
        "description": "Jami 10 ta g‘alabaga erishing.",
        "reward_pul": 200,
        "reward_almas": 1,
    },
    "first_damage": {
        "name": "💥 Birinchi zarba",
        "description": "Jangda damage yetkazing.",
        "reward_pul": 25,
        "reward_almas": 0,
    },
    "one_thousand_damage": {
        "name": "💣 1000 Damage",
        "description": "Jami 1000 damage yetkazing.",
        "reward_pul": 150,
        "reward_almas": 0,
    },
    "five_thousand_damage": {
        "name": "🔥 5000 Damage",
        "description": "Jami 5000 damage yetkazing.",
        "reward_pul": 300,
        "reward_almas": 1,
    },
    "three_win_streak": {
        "name": "🔥 3 Streak",
        "description": "3 ta ketma-ket g‘alabaga erishing.",
        "reward_pul": 100,
        "reward_almas": 0,
    },
    "five_win_streak": {
        "name": "⚡ 5 Streak",
        "description": "5 ta ketma-ket g‘alabaga erishing.",
        "reward_pul": 200,
        "reward_almas": 1,
    },
    "ten_win_streak": {
        "name": "💎 10 Streak",
        "description": "10 ta ketma-ket g‘alabaga erishing.",
        "reward_pul": 500,
        "reward_almas": 2,
    },
    "veteran": {
        "name": "🛡️ Veteran",
        "description": "Jami 25 ta jang o‘tkazing.",
        "reward_pul": 500,
        "reward_almas": 1,
    },
}


def get_user_achievements(user):
    value = user.get("achievements", [])

    if not isinstance(value, list):
        value = []

    return value


def check_achievements(user):
    wins = int(user.get("battle_wins", user.get("wins", 0)))
    losses = int(user.get("battle_losses", user.get("losses", 0)))
    damage = int(user.get("battle_damage", 0))
    streak = int(user.get("win_streak", 0))
    battles = wins + losses

    unlocked = get_user_achievements(user)

    conditions = {
        "first_win": wins >= 1,
        "five_wins": wins >= 5,
        "ten_wins": wins >= 10,
        "first_damage": damage > 0,
        "one_thousand_damage": damage >= 1000,
        "five_thousand_damage": damage >= 5000,
        "three_win_streak": streak >= 3,
        "five_win_streak": streak >= 5,
        "ten_win_streak": streak >= 10,
        "veteran": battles >= 25,
    }

    newly_unlocked = []

    for achievement_id, condition in conditions.items():
        if not condition:
            continue

        if achievement_id in unlocked:
            continue

        unlocked.append(achievement_id)

        achievement = ACHIEVEMENTS[achievement_id]

        user["pul"] = int(user.get("pul", 0)) + int(
            achievement.get("reward_pul", 0)
        )

        user["almas"] = int(user.get("almas", 0)) + int(
            achievement.get("reward_almas", 0)
        )

        newly_unlocked.append(achievement_id)

    user["achievements"] = unlocked

    return newly_unlocked


def achievements_text(user):
    unlocked = get_user_achievements(user)

    lines = [
        "🏅 ACHIEVEMENTLAR",
        "━━━━━━━━━━━━━━",
        "",
    ]

    for achievement_id, achievement in ACHIEVEMENTS.items():
        if achievement_id in unlocked:
            status = "✅"
        else:
            status = "🔒"

        lines.append(
            f"{status} {achievement['name']}"
        )

    return "\n".join(lines)
