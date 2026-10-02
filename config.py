import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_FILE)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

try:
    MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", "0"))
except ValueError:
    MAIN_ADMIN_ID = 0

DATA_FILE = os.path.join(
    BASE_DIR,
    "data",
    "users.json"
)

MAX_HP = 100
MAX_MEDKITS = 3

MAX_WEAPON_LEVEL = 15
WEAPON_XP_PER_LEVEL = 1000

WIN_STREAK_FOR_ALMAS = 10
TEAM_BONUS = 50

    
# ⚔️ Jang timer variantlari
BATTLE_TIMER_OPTIONS = (10, 20, 30, 40, 50, 60)
DEFAULT_BATTLE_TIMER = 10

ATTACK_ENERGY_COST = 10
ROUND_ENERGY_REGEN = 10
WEAPON_XP_PER_ATTACK = 100
