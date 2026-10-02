import json
import os

from config import DATA_FILE, MAIN_ADMIN_ID


DEFAULT_DATA = {
    "users": {},
    "admins": [],
    "settings": {
        "win_reward": 50,
        "team_bonus": 50,
        "win_streak_for_almas": 10
    }
}


def _ensure_file():
    folder = os.path.dirname(DATA_FILE)

    if folder:
        os.makedirs(folder, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA.copy())


def load_data():
    _ensure_file()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("users", {})
    data.setdefault("admins", [])
    data.setdefault("group_settings", {})
    data.setdefault("stats_history", {})
    data.setdefault("groups", {})

    # 🏆 TOP statistikasi uchun eski foydalanuvchilarni tayyorlash
    for _uid, _user in data["users"].items():
        if not isinstance(_user, dict):
            continue

        _user.setdefault("battles", 0)
        _user.setdefault("attacks", 0)
        _user.setdefault("defenses_used", 0)
        _user.setdefault("medkits_used", 0)
        _user.setdefault("kills", int(_user.get("battle_kills", 0)))
        _user.setdefault("damage_dealt", int(_user.get("battle_damage", 0)))
        _user.setdefault("pul_earned", 0)
        _user.setdefault("almas_earned", 0)
        _user.setdefault("weapon_xp_earned", 0)
        _user.setdefault("last_activity", None)

    # 👥 Guruh statistikasi uchun xavfsiz boshlang‘ich maydonlar
    for _gid, _group in data["groups"].items():
        if not isinstance(_group, dict):
            continue

        _group.setdefault("chat_id", int(_gid) if str(_gid).lstrip("-").isdigit() else _gid)
        _group.setdefault("title", "Noma’lum guruh")
        _group.setdefault("first_seen", None)
        _group.setdefault("last_seen", None)
        _group.setdefault("battles", 0)
        _group.setdefault("players", 0)
        _group.setdefault("damage", 0)
        _group.setdefault("wins", 0)
        _group.setdefault("defenses", 0)
        _group.setdefault("medkits", 0)
        _group.setdefault("premium_plan", None)
        _group.setdefault("premium_until", None)
        _group.setdefault("premium_active", False)

    # 📊 Eski foydalanuvchilarga yangi jang statistikalarini qo‘shish
    for _uid, _user in data["users"].items():
        if isinstance(_user, dict):
            _user.setdefault("battle_wins", 0)
            _user.setdefault("battle_losses", 0)
            _user.setdefault("battle_damage", 0)
            _user.setdefault("battle_kills", 0)
            _user.setdefault("inventory", {})
            _user.setdefault("equipped_weapon", "pistol")
            _user.setdefault("weapon_xp", {})
            _user.setdefault("weapon_levels", {})
            _user.setdefault("defense_hp", 0)

    data.setdefault("settings", {})

    data["settings"].setdefault("win_reward", 50)
    data["settings"].setdefault("team_bonus", 50)
    data["settings"].setdefault("win_streak_for_almas", 10)
    data["settings"].setdefault("premium_plans", {
        "1_kun": {"name": "⏱️ 1 kun", "days": 1, "price": 5},
        "3_kun": {"name": "📅 3 kun", "days": 3, "price": 10},
        "1_hafta": {"name": "📅 1 hafta", "days": 7, "price": 20},
        "2_hafta": {"name": "📅 2 hafta", "days": 14, "price": 35},
        "1_oy": {"name": "📅 1 oy", "days": 30, "price": 60},
        "3_oy": {"name": "📅 3 oy", "days": 90, "price": 150},
        "6_oy": {"name": "📆 6 oy", "days": 180, "price": 280},
        "1_yil": {"name": "📆 1 yil", "days": 365, "price": 500},
        "cheksiz": {"name": "♾️ Cheksiz", "days": None, "price": 1000}
    })
    data["settings"].setdefault("premium_plans", {
        "1_kun": {"name": "⏱️ 1 kun", "days": 1, "price": 5},
        "3_kun": {"name": "📅 3 kun", "days": 3, "price": 10},
        "1_hafta": {"name": "📅 1 hafta", "days": 7, "price": 25},
        "2_hafta": {"name": "📅 2 hafta", "days": 14, "price": 40},
        "1_oy": {"name": "📅 1 oy", "days": 30, "price": 70},
        "3_oy": {"name": "📅 3 oy", "days": 90, "price": 180},
        "6_oy": {"name": "📆 6 oy", "days": 180, "price": 320},
        "1_yil": {"name": "📆 1 yil", "days": 365, "price": 550},
        "cheksiz": {"name": "♾️ Cheksiz", "days": None, "price": 1500}
    })

    return data


def save_data(data):
    folder = os.path.dirname(DATA_FILE)

    if folder:
        os.makedirs(folder, exist_ok=True)

    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

    os.replace(temp_file, DATA_FILE)


def ensure_user(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "pul": 0,
            "almas": 0,
            "win_streak": 0,
            "wins": 0,
            "losses": 0,
            "hp": 100,
            "energy": 100,
            "defense": 1,
            "medkits": 3,
            "battle_wins": 0,
            "battle_losses": 0,
            "battle_damage": 0,
            "battle_kills": 0,
            "inventory": {},
            "equipped_weapon": "pistol",
            "weapon_xp": {},
            "weapon_levels": {},
            "defense_hp": 0
        }
        save_data(data)

    return data


def get_user(user_id):
    data = load_data()
    return data["users"].get(str(user_id))


def update_user(user_id, **changes):
    data = ensure_user(user_id)
    uid = str(user_id)

    data["users"][uid].update(changes)
    save_data(data)

    return data["users"][uid]


def is_admin(user_id):
    data = load_data()

    if int(user_id) == MAIN_ADMIN_ID:
        return True

    return int(user_id) in data.get("admins", [])


def add_admin(user_id):
    data = load_data()
    user_id = int(user_id)

    if user_id not in data["admins"]:
        data["admins"].append(user_id)
        save_data(data)

    return True


def remove_admin(user_id):
    data = load_data()
    user_id = int(user_id)

    if user_id in data["admins"]:
        data["admins"].remove(user_id)
        save_data(data)

    return True
