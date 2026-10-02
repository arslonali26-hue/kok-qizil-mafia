from __future__ import annotations

from typing import Any


# 🧩 Universal Effect Engine
# Yangi effekt turlarini shu ro‘yxatga qo‘shish mumkin.
EFFECT_TYPES = {
    "hp": {
        "name": "❤️ HP",
        "value_type": "int",
    },
    "energy": {
        "name": "⚡ Energy",
        "value_type": "int",
    },
    "defense_hp": {
        "name": "🛡 Himoya HP",
        "value_type": "int",
    },
    "pul": {
        "name": "💰 Pul",
        "value_type": "int",
    },
    "almas": {
        "name": "💎 Almas",
        "value_type": "int",
    },
    "xp": {
        "name": "✨ XP",
        "value_type": "int",
    },
    "next_heal_multiplier": {
        "name": "🩹 Keyingi davolash ko‘paytirgichi",
        "value_type": "float",
    },
    "uses": {
        "name": "🔢 Foydalanish soni",
        "value_type": "int",
    },
    "duration": {
        "name": "⏱ Davomiylik",
        "value_type": "int",
    },
    "random_reward": {
        "name": "🎁 Tasodifiy mukofot",
        "value_type": "int",
    },
    "grant_item": {
        "name": "📦 Tovar berish",
        "value_type": "int",
    },
    "unlock_feature": {
        "name": "🔓 Imkoniyat ochish",
        "value_type": "int",
    },
}


def normalize_effect(effect: Any) -> dict:
    """
    Effektni yagona formatga keltiradi.
    """

    if not isinstance(effect, dict):
        return {}

    effect_type = str(effect.get("effect_type", "")).strip()

    if effect_type not in EFFECT_TYPES:
        return {}

    result = {
        "effect_type": effect_type,
        "value": effect.get("value", 0),
    }

    if "duration" in effect:
        result["duration"] = effect.get("duration")

    if "uses" in effect:
        result["uses"] = effect.get("uses")

    if "conditions" in effect:
        result["conditions"] = effect.get("conditions")

    return result


def normalize_effects(effects: Any) -> list[dict]:
    """
    Mahsulotdagi barcha effektlarni tekshiradi.
    """

    if not isinstance(effects, list):
        return []

    result = []

    for effect in effects:
        normalized = normalize_effect(effect)

        if normalized:
            result.append(normalized)

    return result


def create_effect(
    effect_type: str,
    value: int | float = 0,
    duration: int | None = None,
    uses: int | None = None,
    conditions: dict | None = None,
) -> dict:
    """
    Universal effekt yaratadi.
    """

    effect_type = str(effect_type).strip()

    if effect_type not in EFFECT_TYPES:
        raise ValueError(
            f"Noma’lum effekt turi: {effect_type}"
        )

    effect = {
        "effect_type": effect_type,
        "value": value,
    }

    if duration is not None:
        effect["duration"] = duration

    if uses is not None:
        effect["uses"] = uses

    if conditions is not None:
        effect["conditions"] = conditions

    return effect


def effect_name(effect_type: str) -> str:
    """
    Effektning emoji + nomini qaytaradi.
    """

    info = EFFECT_TYPES.get(effect_type)

    if not info:
        return f"⚙️ {effect_type}"

    return info["name"]


def describe_effect(effect: dict) -> str:
    """
    Effektni odam tushunadigan ko‘rinishda chiqaradi.
    """

    effect = normalize_effect(effect)

    if not effect:
        return "⚙️ Noma’lum effekt"

    effect_type = effect["effect_type"]
    value = effect.get("value", 0)

    text = f"{effect_name(effect_type)}: {value}"

    if effect.get("uses") is not None:
        text += f" | 🔢 {effect['uses']} marta"

    if effect.get("duration") is not None:
        text += f" | ⏱ {effect['duration']}"

    return text


def describe_effects(effects: list[dict]) -> list[str]:
    """
    Mahsulotdagi barcha effektlarni matnga aylantiradi.
    """

    return [
        describe_effect(effect)
        for effect in normalize_effects(effects)
    ]



def get_active_effects(user: dict) -> list[dict]:
    """
    Foydalanuvchining aktiv effektlarini qaytaradi.
    """
    active = user.get("active_effects", [])

    if not isinstance(active, list):
        active = []

    user["active_effects"] = active
    return active


def add_active_effect(
    user: dict,
    effect: dict,
) -> dict:
    """
    Effektni foydalanuvchining aktiv effektlariga qo‘shadi.
    """

    normalized = normalize_effect(effect)

    if not normalized:
        raise ValueError("Noto‘g‘ri effekt")

    active = get_active_effects(user)

    stored = dict(normalized)

    if "uses" in stored:
        try:
            stored["uses_remaining"] = max(
                0,
                int(stored["uses"])
            )
        except (TypeError, ValueError):
            stored["uses_remaining"] = 0

    if "duration" in stored:
        try:
            stored["duration_remaining"] = max(
                0,
                int(stored["duration"])
            )
        except (TypeError, ValueError):
            stored["duration_remaining"] = 0

    active.append(stored)
    return stored


def remove_active_effect(
    user: dict,
    index: int,
) -> bool:
    """
    Aktiv effektni indeks orqali o‘chiradi.
    """

    active = get_active_effects(user)

    if index < 0 or index >= len(active):
        return False

    active.pop(index)
    return True


def cleanup_active_effects(user: dict) -> list[dict]:
    """
    Tugagan effektlarni olib tashlaydi.
    """

    active = get_active_effects(user)
    remaining = []

    for effect in active:
        uses_remaining = effect.get("uses_remaining")
        duration_remaining = effect.get("duration_remaining")

        if uses_remaining is not None:
            try:
                if int(uses_remaining) <= 0:
                    continue
            except (TypeError, ValueError):
                continue

        if duration_remaining is not None:
            try:
                if int(duration_remaining) <= 0:
                    continue
            except (TypeError, ValueError):
                continue

        remaining.append(effect)

    user["active_effects"] = remaining
    return remaining


def consume_active_effect(
    user: dict,
    effect_type: str,
) -> dict | None:
    """
    Belgilangan turdagi aktiv effektni bir marta ishlatadi.

    Uses bo‘lsa kamaytiradi.
    Tugasa avtomatik o‘chadi.
    """

    active = get_active_effects(user)

    for index, effect in enumerate(active):
        if effect.get("effect_type") != effect_type:
            continue

        if "uses_remaining" in effect:
            try:
                effect["uses_remaining"] -= 1
            except (TypeError, ValueError):
                effect["uses_remaining"] = 0

        result = dict(effect)

        cleanup_active_effects(user)

        return result

    return None


def has_active_effect(
    user: dict,
    effect_type: str,
) -> bool:
    """
    Foydalanuvchida aktiv effekt bor-yo‘qligini tekshiradi.
    """

    cleanup_active_effects(user)

    return any(
        effect.get("effect_type") == effect_type
        for effect in get_active_effects(user)
    )


def apply_effects(user: dict, effects: list[dict]) -> list[str]:
    """
    Mahsulot effektlarini foydalanuvchiga amalda qo‘llaydi.

    Bu universal dvigatelning asosiy bajaruvchi qismi.
    """

    messages = []

    for effect in normalize_effects(effects):
        effect_type = effect.get("effect_type")
        value = effect.get("value", 0)

        if effect_type == "hp":
            old = int(user.get("hp", 100))
            new = max(0, min(100, old + int(value)))
            user["hp"] = new

            actual = new - old

            if actual > 0:
                messages.append(f"❤️ HP +{actual}")
            elif actual < 0:
                messages.append(f"❤️ HP {actual}")
            else:
                messages.append("❤️ HP o‘zgarmadi")

        elif effect_type == "energy":
            old = int(user.get("energy", 100))
            new = max(0, min(100, old + int(value)))
            user["energy"] = new

            actual = new - old

            if actual > 0:
                messages.append(f"⚡ Energy +{actual}")
            elif actual < 0:
                messages.append(f"⚡ Energy {actual}")
            else:
                messages.append("⚡ Energy o‘zgarmadi")

        elif effect_type == "pul":
            old = int(user.get("pul", 0))
            new = max(0, old + int(value))
            user["pul"] = new

            actual = new - old

            if actual >= 0:
                messages.append(f"💰 Pul +{actual:,}")
            else:
                messages.append(f"💰 Pul {actual:,}")

        elif effect_type == "almas":
            old = int(user.get("almas", 0))
            new = max(0, old + int(value))
            user["almas"] = new

            actual = new - old

            if actual >= 0:
                messages.append(f"💎 Almas +{actual:,}")
            else:
                messages.append(f"💎 Almas {actual:,}")

        elif effect_type == "xp":
            old = int(user.get("xp", 0))
            new = max(0, old + int(value))
            user["xp"] = new

            actual = new - old
            messages.append(f"✨ XP +{actual:,}")

        elif effect_type == "next_heal_multiplier":
            multiplier = float(value)

            if multiplier <= 0:
                continue

            active_effect = dict(effect)
            active_effect["value"] = multiplier

            add_active_effect(
                user,
                active_effect,
            )

            user["next_heal_multiplier"] = multiplier

            if multiplier.is_integer():
                multiplier_text = str(int(multiplier))
            else:
                multiplier_text = str(multiplier)

            messages.append(
                f"🩹 Keyingi davolash ×{multiplier_text}"
            )

        elif effect_type == "uses":
            if int(value) <= 0:
                continue

            active_effect = create_effect(
                "uses",
                int(value),
            )

            add_active_effect(
                user,
                active_effect,
            )

            messages.append(
                f"🔢 Effekt foydalanishi: {int(value)} marta"
            )

        elif effect_type == "duration":
            if int(value) <= 0:
                continue

            active_effect = create_effect(
                "duration",
                int(value),
            )

            add_active_effect(
                user,
                active_effect,
            )

            messages.append(
                f"⏱ Effekt davomiyligi: {int(value)}"
            )

        elif effect_type == "defense_hp":
            # Jang mexanikasiga tegmaslik uchun
            # aktiv effekt sifatida saqlanadi.
            active_effect = dict(effect)

            add_active_effect(
                user,
                active_effect,
            )

            messages.append(
                f"🛡 Himoya effekti: +{int(value)}"
            )

        elif effect_type == "random_reward":
            # Universal engine uchun tayanch.
            # Aniq random mukofot konfiguratsiyasi
            # keyingi integratsiyada beriladi.
            add_active_effect(
                user,
                effect,
            )

            messages.append(
                f"🎁 Tasodifiy mukofot effekti saqlandi"
            )

        elif effect_type == "grant_item":
            # Tovar ID / beriladigan miqdor
            # universal state sifatida saqlanadi.
            add_active_effect(
                user,
                effect,
            )

            messages.append(
                f"📦 Tovar berish effekti saqlandi"
            )

        elif effect_type == "unlock_feature":
            add_active_effect(
                user,
                effect,
            )

            messages.append(
                f"🔓 Imkoniyat ochish effekti saqlandi"
            )

    return messages
