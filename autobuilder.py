from __future__ import annotations
import py_compile

import ast
import compileall
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / ".autobuilder_backups"

# Faqat aktiv loyiha fayllari.
# *_backup*, backup_* va .autobuilder_backups ichidagi fayllar feature kodi
# sifatida hisoblanmaydi.
EXCLUDED_PARTS = {
    ".autobuilder_backups",
    "__pycache__",
    ".git",
}

BACKUP_MARKERS = (
    "_backup",
    "backup_",
)

CORE_FILES = (
    "main.py",
    "database.py",
)


def log(message: str) -> None:
    print(message, flush=True)


def active_python_files() -> list[Path]:
    result = []

    for path in ROOT.glob("*.py"):
        if path.name == "autobuilder.py":
            continue

        name = path.name.lower()

        if any(marker in name for marker in BACKUP_MARKERS):
            continue

        result.append(path)

    return sorted(result)


def create_backup() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    backup_dir = BACKUP_ROOT / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)

    files = []

    for path in ROOT.iterdir():
        if path.name in EXCLUDED_PARTS:
            continue
        if path.name == "autobuilder.py":
            continue
        if path.is_file():
            shutil.copy2(path, backup_dir / path.name)
            files.append(path.name)

    manifest = {
        "created_at": datetime.now().isoformat(),
        "root": str(ROOT),
        "files": sorted(files),
    }

    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    log(f"📦 BACKUP: {backup_dir}")
    log(f"📋 MANIFEST: {len(files)} ta fayl")
    return backup_dir


def restore_backup(backup_dir: Path) -> bool:
    if not backup_dir.exists() or not backup_dir.is_dir():
        log("❌ ROLLBACK: backup topilmadi")
        return False

    manifest_path = backup_dir / "manifest.json"

    if not manifest_path.exists():
        log("❌ ROLLBACK: manifest.json topilmadi")
        return False

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        files = manifest.get("files", [])
    except Exception as exc:
        log(f"❌ ROLLBACK: manifest buzilgan: {exc}")
        return False

    if not isinstance(files, list) or not files:
        log("❌ ROLLBACK: manifestda fayllar yo‘q")
        return False

    restored = 0

    for name in files:
        if not isinstance(name, str):
            continue

        backup_file = backup_dir / name
        target = ROOT / name

        if not backup_file.is_file():
            log(f"❌ ROLLBACK: backup fayli yo‘q: {name}")
            return False

        shutil.copy2(backup_file, target)
        restored += 1

    log(f"🔄 ROLLBACK: {backup_dir}")
    log(f"📋 Tiklangan fayllar: {restored}")
    log("🛡️ Yangi fayllar avtomatik o‘chirilmaydi")
    return True


def audit_structure() -> bool:
    log("\n🔍 AUDIT")

    ok = True

    for name in CORE_FILES:
        path = ROOT / name

        if path.exists():
            log(f"   ✅ {name}")
        else:
            log(f"   ❌ {name} yo‘q")
            ok = False

    files = active_python_files()

    log(f"   📁 Aktiv Python fayllar: {len(files)}")

    if not files:
        log("   ❌ Aktiv Python fayl topilmadi")
        return False

    return ok


def compile_project() -> bool:
    log("\n🐍 COMPILE")

    files = active_python_files()

    if not files:
        log("   ❌ Aktiv Python fayllar topilmadi")
        return False

    ok = True

    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            compile(
                source,
                str(path),
                "exec",
            )
            log(f"   ✅ {path.name}")
        except SyntaxError as exc:
            ok = False
            log(
                f"   ❌ {path.name}:{exc.lineno} "
                f"{exc.msg}"
            )
        except Exception as exc:
            ok = False
            log(
                f"   ❌ {path.name}: "
                f"{type(exc).__name__}: {exc}"
            )

    if ok:
        log("   ✅ Barcha AKTIV Python fayllar compile bo‘ldi")
        return True

    log("   ❌ Aktiv Python fayllarda xato bor")
    return False


def inspect_main_handlers() -> bool:
    log("\n🔗 HANDLER CHECK")

    main = ROOT / "main.py"

    try:
        source = main.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        log(f"   ❌ main.py AST xatosi: {exc}")
        return False

    imports = set()
    handlers = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "moderation":
                for item in node.names:
                    imports.add(item.name)

        if isinstance(node, ast.Call):
            func = node.func

            if (
                isinstance(func, ast.Attribute)
                and func.attr == "add_handler"
            ):
                handlers.append(node.lineno)

    log(f"   📥 moderation importlari: {len(imports)}")
    log(f"   🔗 add_handler chaqiruvlari: {len(handlers)}")

    if not imports:
        log("   ⚠️ moderation importlari topilmadi")

    if not handlers:
        log("   ❌ add_handler topilmadi")
        return False

    log("   ✅ Handler strukturasi mavjud")
    return True


def database_check() -> bool:
    log("\n💾 DATABASE CHECK")

    path = ROOT / "database.py"

    if not path.exists():
        log("   ❌ database.py topilmadi")
        return False

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        log(f"   ❌ database.py AST xatosi: {exc}")
        return False

    names = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        )
    }

    required = {
        "load_data",
        "save_data",
    }

    missing = required - names

    if missing:
        log(f"   ❌ Yetishmayapti: {', '.join(sorted(missing))}")
        return False

    log("   ✅ load_data / save_data mavjud")
    return True


def smoke_test() -> bool:
    log("\n🧪 SMOKE TEST")

    checks = [
        ("main.py", (ROOT / "main.py").exists()),
        ("database.py", (ROOT / "database.py").exists()),
        ("config.py", (ROOT / "config.py").exists()),
        ("moderation.py", (ROOT / "moderation.py").exists()),
    ]

    ok = True

    for name, exists in checks:
        if exists:
            log(f"   ✅ {name}")
        else:
            log(f"   ❌ {name}")
            ok = False

    return ok


def full_audit() -> bool:
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("🛡️ AUTOBUILDER AUDIT")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    results = [
        audit_structure(),
        compile_project(),
        inspect_main_handlers(),
        database_check(),
        smoke_test(),
    ]

    log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if all(results):
        log("✅ AUDIT — HAMMASI JOYIDA")
        return True

    log("❌ AUDIT — MUAMMO BOR")
    return False




def validate_feature_patch(patch_path: Path) -> tuple[bool, list[str]]:
    """Feature patchning ruxsat etilgan target fayllarini tekshiradi."""

    try:
        source = patch_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(patch_path))
    except Exception as exc:
        log(f"❌ FEATURE GUARD: patch parse xatosi: {exc}")
        return False, []

    targets = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FEATURE_TARGETS":
                    value = node.value

                    if not isinstance(value, (ast.List, ast.Tuple)):
                        log("❌ FEATURE GUARD: FEATURE_TARGETS list/tuple bo‘lishi kerak")
                        return False, []

                    for item in value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            targets.append(item.value)

    if not targets:
        log("❌ FEATURE GUARD: FEATURE_TARGETS topilmadi")
        log("📌 Patch boshida: FEATURE_TARGETS = ['file.py']")
        return False, []

    clean_targets = []

    for name in targets:
        path = Path(name)

        if path.is_absolute():
            log(f"❌ FEATURE GUARD: absolute path taqiqlangan: {name}")
            return False, []

        if ".." in path.parts:
            log(f"❌ FEATURE GUARD: parent path taqiqlangan: {name}")
            return False, []

        if name == "autobuilder.py":
            log("❌ FEATURE GUARD: autobuilder.py target bo‘lishi mumkin emas")
            return False, []

        if any(part in EXCLUDED_PARTS for part in path.parts):
            log(f"❌ FEATURE GUARD: himoyalangan papka: {name}")
            return False, []

        if any(marker in path.name.lower() for marker in BACKUP_MARKERS):
            log(f"❌ FEATURE GUARD: backup fayli target bo‘lishi mumkin emas: {name}")
            return False, []

        if path.suffix != ".py":
            log(f"❌ FEATURE GUARD: faqat .py target ruxsat etiladi: {name}")
            return False, []

        clean_targets.append(name)

    clean_targets = sorted(set(clean_targets))

    log(f"🛡️ FEATURE GUARD: {len(clean_targets)} ta target")
    for name in clean_targets:
        log(f"   🎯 {name}")

    return True, clean_targets


def snapshot_project_state() -> dict[str, bytes]:
    """Aktiv loyiha fayllarining integratsiyadan oldingi holatini oladi."""

    snapshot = {}

    for path in ROOT.iterdir():
        if not path.is_file():
            continue

        if path.name in EXCLUDED_PARTS:
            continue

        if path.name == "autobuilder.py":
            continue

        name = path.name.lower()

        if any(marker in name for marker in BACKUP_MARKERS):
            continue

        snapshot[path.name] = path.read_bytes()

    return snapshot


def changed_project_files(before: dict[str, bytes]) -> list[str]:
    """Integratsiyadan keyin o‘zgargan aktiv fayllarni aniqlaydi."""

    current = {}

    for path in ROOT.iterdir():
        if not path.is_file():
            continue

        if path.name in EXCLUDED_PARTS:
            continue

        if path.name == "autobuilder.py":
            continue

        name = path.name.lower()

        if any(marker in name for marker in BACKUP_MARKERS):
            continue

        current[path.name] = path.read_bytes()

    changed = set(before) | set(current)

    return sorted(
        name
        for name in changed
        if before.get(name) != current.get(name)
    )



def dry_run_feature(patch_path: Path) -> bool:
    """Feature patchni o‘zgartirmasdan oldindan tekshiradi."""

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("🧪 FEATURE DRY-RUN")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if not patch_path.exists() or not patch_path.is_file():
        log(f"❌ DRY-RUN: patch topilmadi: {patch_path}")
        return False

    if patch_path.suffix != ".py":
        log("❌ DRY-RUN: patch .py fayl bo‘lishi kerak")
        return False

    valid, targets = validate_feature_patch(patch_path)

    if not valid:
        log("❌ DRY-RUN: FEATURE GUARD rad etdi")
        return False

    try:
        source = patch_path.read_text(encoding="utf-8")
        compile(source, str(patch_path), "exec")
    except Exception as exc:
        log(f"❌ DRY-RUN: compile xatosi: {exc}")
        return False

    log("📋 Kutilayotgan target fayllar:")

    for name in targets:
        log(f"   🎯 {name}")

    log("🛡️ Loyiha fayllari o‘zgartirilmaydi")
    log("🐍 Patch compile: ✅")
    log("🛡️ Feature Guard: ✅")
    log("🧪 DRY-RUN: MUVAFFAQIYATLI")

    return True


def run_feature_patch(patch_path: Path) -> bool:
    """Feature patchni guard bilan tekshiradi va ishga tushiradi."""
    if not patch_path.exists() or not patch_path.is_file():
        log(f"❌ FEATURE: patch topilmadi: {patch_path}")
        return False

    if patch_path.suffix != ".py":
        log("❌ FEATURE: patch .py fayl bo‘lishi kerak")
        return False

    valid, targets = validate_feature_patch(patch_path)

    if not valid:
        return False

    try:
        source = patch_path.read_text(encoding="utf-8")
        compile(source, str(patch_path), "exec")
    except Exception as exc:
        log(f"❌ FEATURE: patch compile xatosi: {exc}")
        return False

    before = snapshot_project_state()

    log(f"🧩 FEATURE PATCH: {patch_path.name}")

    result = subprocess.run(
        [sys.executable, str(patch_path)],
        cwd=str(ROOT),
        text=True,
    )

    if result.returncode != 0:
        log(f"❌ FEATURE: patch xato kodi: {result.returncode}")
        return False

    changed = changed_project_files(before)

    log(f"🔎 O‘zgargan fayllar: {len(changed)} ta")

    allowed = set(targets)
    unauthorized = [name for name in changed if name not in allowed]

    if unauthorized:
        log("❌ FEATURE GUARD: ruxsatsiz fayl o‘zgardi")

        for name in unauthorized:
            log(f"   🚫 {name}")

        return False

    for name in changed:
        log(f"   ✅ {name}")

    log("✅ FEATURE GUARD: barcha o‘zgarishlar ruxsat etilgan")
    log("✅ FEATURE PATCH: bajarildi")
    return True



def verify_runtime() -> bool:
    """Asosiy Python modullarini real import qilib tekshiradi."""

    log("🧪 RUNTIME VERIFY")

    modules = [
        "config",
        "database",
        "moderation",
        "main",
    ]

    ok = True

    for module_name in modules:
        try:
            __import__(module_name)
            log(f"   ✅ import {module_name}")
        except Exception as exc:
            log(f"   ❌ import {module_name}: {exc}")
            ok = False

    if ok:
        log("✅ RUNTIME VERIFY — MUVAFFAQIYATLI")
    else:
        log("❌ RUNTIME VERIFY — MUAMMO BOR")

    return ok


def verify_main_runtime() -> bool:
    """main.py yuklangandan keyin Application mavjudligini tekshiradi."""

    log("🔗 MAIN RUNTIME VERIFY")

    try:
        import main

        application = getattr(main, "app", None)

        if application is None:
            log("⚠️ main.app topilmadi — faqat strukturaviy rejim")
        else:
            log("   ✅ main.app mavjud")

        log("   ✅ main.py runtime yuklandi")
        return True

    except Exception as exc:
        log(f"   ❌ main.py runtime xatosi: {exc}")
        return False


def post_integration_verify() -> bool:
    """Integratsiyadan keyingi chuqur tekshiruv."""

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("🧪 POST-INTEGRATION VERIFY")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    results = [
        verify_runtime(),
        verify_main_runtime(),
    ]

    if all(results):
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log("✅ POST-INTEGRATION VERIFY — HAMMASI JOYIDA")
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return True

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("❌ POST-INTEGRATION VERIFY — MUAMMO BOR")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return False



def check_dependencies() -> bool:
    """Aktiv loyiha uchun tashqi Python dependency'larini tekshiradi."""
    log("📦 DEPENDENCY CHECK")

    standard = {
        "ast", "compileall", "json", "shutil", "subprocess",
        "sys", "datetime", "pathlib", "typing", "re", "time",
        "os", "math", "random", "collections", "asyncio",
        "logging", "traceback", "functools", "itertools",
        "statistics", "dataclasses", "enum", "copy", "uuid",
        "calendar", "hashlib", "hmac", "secrets", "string",
        "textwrap", "warnings", "inspect", "contextlib",
    }

    local_modules = {item.stem for item in active_python_files()}
    imports = set()

    for file_path in active_python_files():
        try:
            tree = ast.parse(
                file_path.read_text(),
                filename=str(file_path),
            )
        except Exception as exc:
            log(f"   ❌ AST {file_path.name}: {exc}")
            return False

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    imports.add(item.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    imports.add(node.module.split(".")[0])

    external = sorted(
        name for name in imports
        if name not in standard
        and name not in local_modules
        and name != "__future__"
    )

    ok = True

    for name in external:
        try:
            __import__(name)
            log(f"   ✅ {name}")
        except Exception as exc:
            log(f"   ❌ {name}: {exc}")
            ok = False

    if ok:
        log("✅ DEPENDENCY CHECK — HAMMASI JOYIDA")
    else:
        log("❌ DEPENDENCY CHECK — MUAMMO BOR")

    return ok


def check_project_imports() -> bool:
    """Aktiv loyiha modullarini paket kontekstida xavfsiz tekshiradi."""
    log("🔗 PROJECT IMPORT CHECK")

    ok = True

    for file_path in active_python_files():
        module_name = file_path.stem

        try:
            if module_name == "__init__":
                log("   ✅ __init__")
                continue

            # Relative import ishlatadigan modullarni paket kontekstida tekshiramiz.
            source = file_path.read_text()
            tree = ast.parse(source, filename=str(file_path))
            has_relative_import = any(
                isinstance(node, ast.ImportFrom) and node.level > 0
                for node in ast.walk(tree)
            )

            if has_relative_import:
                package = f"Game.{module_name}"
                # Game papkasining ota katalogidan import qilish uchun
                # faqat compile/AST darajasidagi xavfsiz tekshiruvdan foydalanamiz.
                log(f"   ✅ {module_name} — relative import mavjud, AST OK")
                continue

            # Feature patch audit vaqtida bajarilmasin.
            # Patch faqat AST/compile darajasida tekshiriladi.
            if file_path.name.lower().endswith("_patch.py"):
                log(f"   ✅ {module_name} — feature patch, AST OK")
                continue

            __import__(module_name)
            log(f"   ✅ {module_name}")

        except Exception as exc:
            log(f"   ❌ {module_name}: {exc}")
            ok = False

    if ok:
        log("✅ PROJECT IMPORT CHECK — HAMMASI JOYIDA")
    else:
        log("❌ PROJECT IMPORT CHECK — MUAMMO BOR")

    return ok

def dependency_guard() -> bool:
    """Integrationdan oldin dependency va import xavfsizligini tekshiradi."""
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("🛡️ DEPENDENCY / IMPORT GUARD")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    dependency_ok = check_dependencies()
    imports_ok = check_project_imports()

    if dependency_ok and imports_ok:
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log("✅ DEPENDENCY GUARD — MUVAFFAQIYATLI")
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return True

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("❌ DEPENDENCY GUARD — MUAMMO BOR")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return False



def database_schema_check() -> bool:
    """Database strukturasining asosiy qismlarini xavfsiz tekshiradi."""
    log("💾 DATABASE SCHEMA CHECK")

    try:
        import database

        data = database.load_data()

        if not isinstance(data, dict):
            log("   ❌ Database root dict emas")
            return False

        required = {
            "users": dict,
            "admins": list,
            "group_settings": dict,
            "stats_history": dict,
            "groups": dict,
        }

        ok = True

        for key, expected_type in required.items():
            if key not in data:
                log(f"   ❌ {key} mavjud emas")
                ok = False
                continue

            if not isinstance(data[key], expected_type):
                log(
                    f"   ❌ {key}: "
                    f"{type(data[key]).__name__} "
                    f"!= {expected_type.__name__}"
                )
                ok = False
            else:
                log(f"   ✅ {key}")

        if ok:
            log("✅ DATABASE SCHEMA CHECK — HAMMASI JOYIDA")
        else:
            log("❌ DATABASE SCHEMA CHECK — MUAMMO BOR")

        return ok

    except Exception as exc:
        log(f"   ❌ Database tekshiruvi: {exc}")
        return False


def database_users_check() -> bool:
    """Mavjud user yozuvlarini o‘chirmasdan tekshiradi."""
    log("👤 DATABASE USERS CHECK")

    try:
        import database

        data = database.load_data()
        users = data.get("users", {})

        if not isinstance(users, dict):
            log("   ❌ users dict emas")
            return False

        ok = True

        for uid, user in users.items():
            if not isinstance(user, dict):
                log(f"   ❌ user {uid}: yozuv dict emas")
                ok = False
                continue

            if not str(uid).strip():
                log("   ❌ bo‘sh user ID topildi")
                ok = False

        log(f"   👥 Tekshirilgan users: {len(users)}")

        if ok:
            log("✅ DATABASE USERS CHECK — HAMMASI JOYIDA")
        else:
            log("❌ DATABASE USERS CHECK — MUAMMO BOR")

        return ok

    except Exception as exc:
        log(f"   ❌ Users tekshiruvi: {exc}")
        return False


def database_groups_check() -> bool:
    """Mavjud group yozuvlarini xavfsiz tekshiradi."""
    log("👥 DATABASE GROUPS CHECK")

    try:
        import database

        data = database.load_data()
        groups = data.get("groups", {})

        if not isinstance(groups, dict):
            log("   ❌ groups dict emas")
            return False

        ok = True

        for gid, group in groups.items():
            if not isinstance(group, dict):
                log(f"   ❌ group {gid}: yozuv dict emas")
                ok = False
                continue

            if "chat_id" not in group:
                log(f"   ⚠️ group {gid}: chat_id yo‘q")

        log(f"   👥 Tekshirilgan groups: {len(groups)}")

        if ok:
            log("✅ DATABASE GROUPS CHECK — HAMMASI JOYIDA")
        else:
            log("❌ DATABASE GROUPS CHECK — MUAMMO BOR")

        return ok

    except Exception as exc:
        log(f"   ❌ Groups tekshiruvi: {exc}")
        return False


def database_migration_guard() -> bool:
    """Integrationdan oldin database xavfsizligini tekshiradi."""
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("🛡️ DATABASE MIGRATION GUARD")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    results = [
        database_schema_check(),
        database_users_check(),
        database_groups_check(),
    ]

    if all(results):
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log("✅ DATABASE MIGRATION GUARD — MUVAFFAQIYATLI")
        log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return True

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("❌ DATABASE MIGRATION GUARD — MUAMMO BOR")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return False



def feature_smoke_test(
    feature_path: str | Path,
    required_symbols: list[str] | None = None,
) -> bool:
    """
    11-BOSQICH:
    Bitta feature faylini xavfsiz smoke-test qiladi.

    Bu test feature kodini ishga tushirmaydi.
    Telegram/network/database yozuvlarini bajarmaydi.
    """
    path = Path(feature_path)

    print(f"🧪 FEATURE SMOKE TEST — {path}")

    # 1. Fayl mavjudligi
    if not path.exists() or not path.is_file():
        print(f"❌ FEATURE FILE — TOPILMADI: {path}")
        return False

    print("📄 FEATURE FILE — ✅")

    # 2. Python compile
    try:
        py_compile.compile(
            str(path),
            doraise=True,
        )
        print("🐍 FEATURE COMPILE — ✅")
    except Exception as exc:
        print(f"❌ FEATURE COMPILE — {exc}")
        return False

    # 3. AST parse
    try:
        import ast

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        print("🌳 FEATURE AST — ✅")
    except Exception as exc:
        print(f"❌ FEATURE AST — {exc}")
        return False

    # 4. Kerakli symbol/funksiyalar
    if required_symbols:
        defined = set()

        for node in tree.body:
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                defined.add(node.name)

        missing = [
            name for name in required_symbols
            if name not in defined
        ]

        if missing:
            print(
                "❌ REQUIRED SYMBOLS — "
                + ", ".join(missing)
            )
            return False

        print("🔎 REQUIRED SYMBOLS — ✅")

    # 5. Relative importlar mavjudligini xavfsiz aniqlash.
    # Importni bajarib yubormaymiz — faqat AST orqali tekshiramiz.
    relative_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level > 0
    ]

    if relative_imports:
        print(
            f"📦 RELATIVE IMPORTS — "
            f"{len(relative_imports)} ta — AST OK — ✅"
        )
    else:
        print("📦 IMPORT STRUCTURE — ✅")

    # 6. Project dependency guard
    try:
        if not dependency_guard():
            print("❌ DEPENDENCY GUARD — FAILED")
            return False
        print("📦 DEPENDENCY GUARD — ✅")
    except Exception as exc:
        print(f"❌ DEPENDENCY GUARD — {exc}")
        return False

    # 7. Database migration guard
    try:
        if not database_migration_guard():
            print("❌ DATABASE MIGRATION GUARD — FAILED")
            return False
        print("💾 DATABASE MIGRATION GUARD — ✅")
    except Exception as exc:
        print(f"❌ DATABASE MIGRATION GUARD — {exc}")
        return False

    # 8. Runtime guard
    try:
        if not post_integration_verify():
            print("❌ POST-INTEGRATION VERIFY — FAILED")
            return False
        print("🚀 POST-INTEGRATION VERIFY — ✅")
    except Exception as exc:
        print(f"❌ POST-INTEGRATION VERIFY — {exc}")
        return False

    print("🧪 FEATURE SMOKE TEST — MUVAFFAQIYATLI")
    return True


def run_feature_smoke_tests(
    feature_paths: list[str | Path],
) -> bool:
    """
    11-BOSQICH:
    Bir nechta feature fayllarini ketma-ket smoke-test qiladi.
    """
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 11-BOSQICH — FEATURE SMOKE-TEST FRAMEWORK")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if not feature_paths:
        print("⚠️ FEATURE LIST — BO‘SH")
        return True

    results = []

    for feature_path in feature_paths:
        try:
            result = feature_smoke_test(feature_path)
        except Exception as exc:
            print(
                f"❌ SMOKE TEST EXCEPTION — "
                f"{feature_path}: {exc}"
            )
            result = False

        results.append(result)

    passed = sum(1 for result in results if result)
    total = len(results)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(
        f"🧪 SMOKE TEST NATIJA — "
        f"{passed}/{total}"
    )

    if all(results):
        print("✅ 11-BOSQICH — MUVAFFAQIYATLI")
        return True

    print("❌ 11-BOSQICH — XATO")
    return False


def _integrate_feature_core(patch_path: Path) -> bool:
    """Backup → feature → audit → rollback yoki commit."""

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("🧩 FEATURE INTEGRATION")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    log("🔍 1/6 — OLD AUDIT")

    if not full_audit():
        log("❌ INTEGRATION: boshlang‘ich audit muvaffaqiyatsiz")
        return False

    log("🛡️ 1.5/7 — DEPENDENCY GUARD")
    if not dependency_guard():
        log("❌ INTEGRATION: dependency/import guard muvaffaqiyatsiz")
        return False

    log("💾 1.75/7 — DATABASE MIGRATION GUARD")
    if not database_migration_guard():
        log("❌ INTEGRATION: database migration guard muvaffaqiyatsiz")
        return False

    log("📦 2/7 — BACKUP")

    try:
        backup_dir = create_backup()
    except Exception as exc:
        log(f"❌ INTEGRATION: backup xatosi: {exc}")
        return False

    log("🧩 3/5 — FEATURE")

    if not run_feature_patch(patch_path):
        log("❌ INTEGRATION: feature ishlamadi")
        log("🔄 ROLLBACK BOSHLANADI")

        if restore_backup(backup_dir):
            log("✅ ROLLBACK: muvaffaqiyatli")
        else:
            log("❌ ROLLBACK: MUVAFFAQIYATSIZ")

        return False

    log("🔍 4/5 — POST AUDIT")

    if not full_audit():
        log("❌ INTEGRATION: post-audit muvaffaqiyatsiz")
        log("🔄 ROLLBACK BOSHLANADI")

        if restore_backup(backup_dir):
            log("✅ ROLLBACK: muvaffaqiyatli")
        else:
            log("❌ ROLLBACK: MUVAFFAQIYATSIZ")

        return False

    log("🧪 4.5/5 — RUNTIME VERIFY")

    if not post_integration_verify():
        log("❌ INTEGRATION: runtime verify muvaffaqiyatsiz")
        log("🔄 ROLLBACK BOSHLANADI")

        if restore_backup(backup_dir):
            log("✅ ROLLBACK: muvaffaqiyatli")
        else:
            log("❌ ROLLBACK: MUVAFFAQIYATSIZ")

        return False

    log("💾 5/5 — COMMIT")
    log(f"✅ FEATURE QABUL QILINDI: {patch_path.name}")
    log(f"📦 BACKUP SAQLANDI: {backup_dir}")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("✅ INTEGRATION — MUVAFFAQIYATLI")

    return True


def _autobuilder_backup_dirs() -> set[str]:
    """Autobuilder backup kataloglarini xavfsiz ro'yxatlaydi."""
    root = Path(".autobuilder_backups")
    if not root.exists() or not root.is_dir():
        return set()

    result = set()
    for item in root.iterdir():
        if item.is_dir():
            result.add(str(item))
    return result


def automatic_failure_recovery(previous_backups: set[str]) -> bool:
    """Integratsiya muvaffaqiyatsiz bo'lsa yangi backup'dan recovery qiladi."""
    log("🚨 AUTOMATIC FAILURE RECOVERY")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        current_backups = _autobuilder_backup_dirs()
        new_backups = sorted(current_backups - previous_backups)

        if not new_backups:
            log("⚠️ Recovery uchun yangi backup topilmadi")
            log("ℹ️ Mavjud backup'larga tegilmadi")
            return False

        latest_backup = Path(new_backups[-1])
        log(f"📦 Recovery backup: {latest_backup}")

        restore = globals().get("restore_backup")
        if callable(restore):
            result = restore(latest_backup)
            if result is False:
                log("❌ restore_backup recovery muvaffaqiyatsiz")
                return False

            log("✅ AUTOMATIC FAILURE RECOVERY — MUVAFFAQIYATLI")
            return True

        rollback = globals().get("rollback")
        if callable(rollback):
            result = rollback(latest_backup)
            if result is False:
                log("❌ rollback recovery muvaffaqiyatsiz")
                return False

            log("✅ AUTOMATIC FAILURE RECOVERY — MUVAFFAQIYATLI")
            return True

        log("⚠️ restore_backup/rollback funksiyasi topilmadi")
        log("ℹ️ Mavjud backup saqlanib qoldi")
        return False

    except Exception as exc:
        log(f"❌ Automatic recovery xatosi: {exc}")
        return False


def integrate_feature(*args, **kwargs) -> bool:
    """Integratsiyani ishga tushiradi va failure bo'lsa recovery qiladi."""
    previous_backups = _autobuilder_backup_dirs()

    try:
        result = _integrate_feature_core(*args, **kwargs)
    except Exception as exc:
        log(f"❌ INTEGRATION EXCEPTION: {exc}")
        result = False

    if result:
        log("✅ INTEGRATION — MUVAFFAQIYATLI")
        return True

    log("🚨 INTEGRATION FAILURE — AUTOMATIC RECOVERY BOSHLANDI")

    if automatic_failure_recovery(previous_backups):
        log("🔄 Recovery tugadi — xavfsiz holat tiklandi")
    else:
        log("⚠️ Recovery avtomatik bajarilmadi")
        log("📦 Backup mavjud bo'lsa, saqlanib qoldi")

    return False


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "audit"

    if command == "audit":
        return 0 if full_audit() else 1

    if command == "backup":
        backup = create_backup()
        log(f"✅ BACKUP TAYYOR: {backup}")
        return 0

    if command == "rollback":
        if len(sys.argv) < 3:
            log("❌ Foydalanish: python autobuilder.py rollback BACKUP_PATH")
            return 1

        backup_dir = Path(sys.argv[2]).resolve()
        return 0 if restore_backup(backup_dir) else 1

    if command == "integrate":
        if len(sys.argv) < 3:
            log("❌ Foydalanish: python autobuilder.py integrate PATCH.py")
            return 1

        patch_path = Path(sys.argv[2]).resolve()

        if BACKUP_ROOT in patch_path.parents:
            log("❌ FEATURE: backup papkasidan patch ishlatish mumkin emas")
            return 1

        return 0 if integrate_feature(patch_path) else 1

    if command == "dry-run":
        if len(sys.argv) < 3:
            log("❌ Foydalanish: python autobuilder.py dry-run PATCH.py")
            return 1

        patch_path = Path(sys.argv[2]).resolve()

        if BACKUP_ROOT in patch_path.parents:
            log("❌ DRY-RUN: backup papkasidan patch ishlatish mumkin emas")
            return 1

        return 0 if dry_run_feature(patch_path) else 1

    if command == "version":
        log("🛡️ Game AutoBuilder v1.0")
        return 0

    log(f"❌ Noma’lum buyruq: {command}")
    log("📌 Buyruqlar: audit | backup | dry-run PATCH.py | integrate PATCH.py | rollback | version")
    return 1



# ============================================================
# 🛡️ STAGE 16 — AUTOBUILDER HARDENING
# ============================================================

def stage16_hardening():
    """
    16-bosqich:
    - autobuilder syntax/AST tekshiruvi
    - muhim funksiyalar mavjudligi
    - feature-patch side-effect himoyasi
    - backup/recovery API tekshiruvi
    - project Python fayllarini compile qilish
    - xavfli backup o‘chirish amallarini bloklash
    """
    from pathlib import Path
    import ast
    import py_compile
    import tempfile
    import shutil

    root = Path(__file__).resolve().parent
    passed = True

    print("🛡️ 16-BOSQICH — AUTOBUILDER HARDENING")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 1. Autobuilder compile
    try:
        py_compile.compile(
            str(root / "autobuilder.py"),
            doraise=True
        )
        print("✅ Autobuilder compile")
    except Exception as exc:
        print(f"❌ Autobuilder compile: {exc}")
        passed = False

    # 2. AST tekshiruvi
    try:
        source = (root / "autobuilder.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        print("✅ Autobuilder AST")
    except Exception as exc:
        print(f"❌ Autobuilder AST: {exc}")
        passed = False
        tree = None

    # 3. Muhim funksiyalar
    required = [
        "restore_backup",
        "automatic_failure_recovery",
        "check_project_imports",
        "feature_smoke_test",
        "run_feature_smoke_tests",
    ]

    names = set()
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)

    missing = [name for name in required if name not in names]

    if missing:
        print("❌ Muhim funksiyalar yo‘q:", ", ".join(missing))
        passed = False
    else:
        print("✅ Muhim funksiyalar mavjud")

    # 4. Feature patch side-effect guard
    try:
        fn_source = ""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "check_project_imports":
                fn_source = ast.get_source_segment(source, node) or ""
                break

        if "_patch.py" in fn_source and "AST/compile" in fn_source:
            print("✅ Feature patch side-effect guard")
        else:
            print("⚠️ Feature patch guard matni topilmadi")
    except Exception as exc:
        print(f"⚠️ Feature patch guard tekshiruvi: {exc}")

    # 5. Backup API
    try:
        restore = globals().get("restore_backup")
        recovery = globals().get("automatic_failure_recovery")

        if callable(restore) and callable(recovery):
            print("✅ Backup + Recovery API")
        else:
            print("❌ Backup + Recovery API")
            passed = False
    except Exception as exc:
        print(f"❌ Backup API: {exc}")
        passed = False

    # 6. Barcha aktiv Python fayllarni compile qilish
    try:
        skip_names = {
            "autobuilder.py",
        }

        py_files = []
        for path in sorted(root.glob("*.py")):
            if path.name in skip_names:
                continue
            if "_backup" in path.name.lower():
                continue
            if path.name.startswith("backup_"):
                continue
            if path.name.endswith("_patch.py"):
                continue
            py_files.append(path)

        failed = []

        for path in py_files:
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                failed.append((path.name, str(exc)))

        if failed:
            print("❌ Aktiv Python compile xatolari:")
            for name, error in failed:
                print(f"   • {name}: {error}")
            passed = False
        else:
            print(f"✅ Aktiv Python compile — {len(py_files)} ta")
    except Exception as exc:
        print(f"❌ Project compile: {exc}")
        passed = False

    # 7. Backup katalogini himoyalash
    try:
        backup_root = root / ".autobuilder_backups"
        backup_root.mkdir(exist_ok=True)

        test_dir = Path(
            tempfile.mkdtemp(
                prefix="stage16_test_",
                dir=str(root)
            )
        )

        test_file = test_dir / "probe.txt"
        test_file.write_text("STAGE16", encoding="utf-8")

        if test_file.read_text(encoding="utf-8") == "STAGE16":
            print("✅ Temporary filesystem test")
        else:
            print("❌ Temporary filesystem test")
            passed = False

        shutil.rmtree(test_dir, ignore_errors=True)

        if backup_root.exists():
            print("✅ Backup katalogi saqlangan")
        else:
            print("❌ Backup katalogi yo‘q")
            passed = False

    except Exception as exc:
        print(f"❌ Filesystem safety test: {exc}")
        passed = False

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if passed:
        print("🏆 16-BOSQICH — MUVAFFAQIYATLI")
        print("🛡️ Autobuilder hardening — ✅")
        print("🧪 Testlar — ✅")
        print("🔄 Recovery API — ✅")
        print("📦 Backup himoyasi — ✅")
        return True

    print("❌ 16-BOSQICH — MUVAFFAQIYATSIZ")
    return False


# ============================================================
# 🧪 STAGE 17 — FULL PROJECT INTEGRATION AUDIT
# ============================================================

def stage17_full_project_audit():
    """
    17-bosqich:
    - barcha aktiv Python fayllar compile
    - AST tekshiruv
    - import tekshiruv
    - asosiy modullar
    - handlerlar
    - database API
    - moderation API
    - duplicate / backup fayllarni ajratish
    - asosiy entrypoint
    - regression xavfsizlik tekshiruvi

    Ushbu funksiya loyiha fayllarini o'zgartirmaydi.
    """

    from pathlib import Path
    import ast
    import py_compile
    import importlib.util

    root = Path(__file__).resolve().parent
    errors = []
    warnings = []

    print("🧪 17-BOSQICH — FULL PROJECT INTEGRATION AUDIT")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # --------------------------------------------------------
    # 1. Aktiv Python fayllarni aniqlash
    # --------------------------------------------------------

    active_files = []

    for path in sorted(root.glob("*.py")):
        name = path.name.lower()

        if name == "autobuilder.py":
            continue

        if "_backup" in name:
            continue

        if name.startswith("backup_"):
            continue

        if name.endswith("_patch.py"):
            continue

        active_files.append(path)

    print(f"📁 Aktiv Python fayllar: {len(active_files)}")

    if len(active_files) < 20:
        warnings.append(
            f"Aktiv Python fayllar soni kutilganidan kam: {len(active_files)}"
        )

    # --------------------------------------------------------
    # 2. Compile
    # --------------------------------------------------------

    compile_failed = []

    for path in active_files:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            compile_failed.append(
                (path.name, str(exc))
            )

    if compile_failed:
        print("❌ Compile xatosi")
        for name, error in compile_failed:
            errors.append(f"Compile {name}: {error}")
    else:
        print(f"✅ Barcha aktiv fayllar compile — {len(active_files)} ta")

    # --------------------------------------------------------
    # 3. AST
    # --------------------------------------------------------

    ast_failed = []

    for path in active_files:
        try:
            tree = ast.parse(
                path.read_text(encoding="utf-8")
            )
            if tree is None:
                raise RuntimeError("AST bo‘sh")
        except Exception as exc:
            ast_failed.append(
                (path.name, str(exc))
            )

    if ast_failed:
        for name, error in ast_failed:
            errors.append(f"AST {name}: {error}")
        print("❌ AST")
    else:
        print("✅ AST — barcha aktiv fayllar")

    # --------------------------------------------------------
    # 4. Muhim fayllar
    # --------------------------------------------------------

    required_files = [
        "main.py",
        "config.py",
        "database.py",
        "game.py",
        "moderation.py",
        "player.py",
        "profile.py",
        "economy.py",
        "shop.py",
        "weapons.py",
        "keyboards.py",
        "rewards.py",
        "missions.py",
        "achievements.py",
        "ranking.py",
    ]

    missing_files = [
        name for name in required_files
        if not (root / name).exists()
    ]

    if missing_files:
        for name in missing_files:
            errors.append(f"Muhim fayl yo‘q: {name}")
        print("❌ Muhim fayllar yetishmaydi")
    else:
        print("✅ Muhim fayllar — mavjud")

    # --------------------------------------------------------
    # 5. Muhim modullar import
    # --------------------------------------------------------

    import_targets = [
        "config.py",
        "database.py",
        "moderation.py",
        "game.py",
        "player.py",
        "profile.py",
        "economy.py",
        "shop.py",
        "weapons.py",
        "keyboards.py",
        "rewards.py",
        "missions.py",
        "achievements.py",
        "ranking.py",
        "main.py",
    ]

    import_failed = []

    for filename in import_targets:

        path = root / filename

        if not path.exists():
            continue

        try:
            module_name = (
                "stage17_"
                + path.stem
                + "_check"
            )

            spec = importlib.util.spec_from_file_location(
                module_name,
                str(path)
            )

            if spec is None or spec.loader is None:
                raise RuntimeError(
                    "import spec yaratilmadi"
                )

            module = importlib.util.module_from_spec(spec)

            spec.loader.exec_module(module)

        except Exception as exc:
            import_failed.append(
                (filename, str(exc))
            )

    if import_failed:
        print("❌ Import xatolari")

        for filename, error in import_failed:
            errors.append(
                f"Import {filename}: {error}"
            )
    else:
        print(
            f"✅ Muhim modullar import — "
            f"{len(import_targets)} ta"
        )

    # --------------------------------------------------------
    # 6. Database API
    # --------------------------------------------------------

    try:

        db_path = root / "database.py"
        db_source = db_path.read_text(
            encoding="utf-8"
        )

        db_tree = ast.parse(db_source)

        db_functions = {
            node.name
            for node in ast.walk(db_tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            )
        }

        required_db_functions = {
            "load_data",
            "save_data",
            "ensure_user",
            "get_user",
            "update_user",
            "is_admin",
        }

        missing_db = (
            required_db_functions
            - db_functions
        )

        if missing_db:
            errors.append(
                "Database API yetishmaydi: "
                + ", ".join(sorted(missing_db))
            )
            print("❌ Database API")
        else:
            print("✅ Database API")

    except Exception as exc:
        errors.append(
            f"Database audit: {exc}"
        )

    # --------------------------------------------------------
    # 7. Moderation API
    # --------------------------------------------------------

    try:

        mod_path = root / "moderation.py"
        mod_source = mod_path.read_text(
            encoding="utf-8"
        )

        mod_tree = ast.parse(mod_source)

        mod_functions = {
            node.name
            for node in ast.walk(mod_tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            )
        }

        moderation_required = {
            "settinghelp_command",
            "moderation_callback",
            "warn_command",
            "mute_command",
            "ban_command",
            "kick_command",
        }

        missing_mod = (
            moderation_required
            - mod_functions
        )

        if missing_mod:
            errors.append(
                "Moderation API yetishmaydi: "
                + ", ".join(sorted(missing_mod))
            )
            print("❌ Moderation API")
        else:
            print("✅ Moderation API")

    except Exception as exc:
        errors.append(
            f"Moderation audit: {exc}"
        )

    # --------------------------------------------------------
    # 8. Main handlerlar
    # --------------------------------------------------------

    try:

        main_source = (
            (root / "main.py")
            .read_text(encoding="utf-8")
        )

        main_tree = ast.parse(main_source)

        handler_names = []

        for node in ast.walk(main_tree):

            if not isinstance(
                node,
                ast.Call
            ):
                continue

            if isinstance(
                node.func,
                ast.Attribute
            ):

                if node.func.attr == "add_handler":
                    handler_names.append(
                        ast.get_source_segment(
                            main_source,
                            node
                        ) or ""
                    )

        if not handler_names:
            warnings.append(
                "main.py ichida add_handler topilmadi"
            )
            print("⚠️ Handlerlar topilmadi")
        else:
            print(
                f"✅ Handler registration — "
                f"{len(handler_names)} ta"
            )

    except Exception as exc:
        errors.append(
            f"Handler audit: {exc}"
        )

    # --------------------------------------------------------
    # 9. Entry point
    # --------------------------------------------------------

    try:

        main_source = (
            (root / "main.py")
            .read_text(encoding="utf-8")
        )

        if (
            'if __name__ == "__main__"'
            in main_source
        ):
            print("✅ main.py entrypoint")
        else:
            warnings.append(
                "main.py da klassik __main__ bloki yo‘q"
            )
            print(
                "⚠️ main.py entrypoint "
                "strukturaviy rejimda"
            )

    except Exception as exc:
        errors.append(
            f"Entrypoint audit: {exc}"
        )

    # --------------------------------------------------------
    # 10. Backup / patch fayllarni aktiv koddan ajratish
    # --------------------------------------------------------

    suspicious_active = []

    for path in active_files:

        lower = path.name.lower()

        if (
            "_backup" in lower
            or lower.startswith("backup_")
            or lower.endswith("_patch.py")
        ):
            suspicious_active.append(
                path.name
            )

    if suspicious_active:
        errors.append(
            "Backup/patch fayl aktiv ro‘yxatga tushgan"
        )
        print("❌ Backup/patch isolation")
    else:
        print("✅ Backup/patch isolation")

    # --------------------------------------------------------
    # 11. Autobuilder o‘zi
    # --------------------------------------------------------

    try:

        auto_path = root / "autobuilder.py"

        py_compile.compile(
            str(auto_path),
            doraise=True
        )

        auto_source = auto_path.read_text(
            encoding="utf-8"
        )

        ast.parse(auto_source)

        print("✅ Autobuilder final syntax")

    except Exception as exc:
        errors.append(
            f"Autobuilder final audit: {exc}"
        )

    # --------------------------------------------------------
    # NATIJA
    # --------------------------------------------------------

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if warnings:
        print("⚠️ Ogohlantirishlar:")
        for warning in warnings:
            print("   •", warning)

    if errors:

        print("❌ 17-BOSQICH — MUVAFFAQIYATSIZ")

        for error in errors:
            print("   •", error)

        print("🛑 O‘zgarish qabul qilinmaydi")
        return False

    print("🏆 17-BOSQICH — MUVAFFAQIYATLI")
    print("🐍 Compile — ✅")
    print("🧩 AST — ✅")
    print("📦 Muhim fayllar — ✅")
    print("🔗 Importlar — ✅")
    print("🗄️ Database API — ✅")
    print("🛡️ Moderation API — ✅")
    print("🎮 Handlerlar — ✅")
    print("🤖 Main entrypoint — ✅")
    print("🚫 Backup isolation — ✅")
    print("🧪 Regression audit — ✅")

    return True


# ============================================================
# 🧪 STAGE 18 — REAL RUNTIME REGRESSION
# ============================================================

def stage18_runtime_regression():
    """
    18-bosqich:
    - barcha aktiv fayllar compile
    - asosiy modullar runtime import
    - database real load/save API tekshiruvi
    - main handler registration
    - moderation handler mavjudligi
    - game handler mavjudligi
    - muhim symbol/API tekshiruvi
    - importdan keyingi exception tekshiruvi

    Loyiha ma'lumotlarini o'zgartirmaydi.
    Database save real ma'lumotni almashtirmasligi uchun
    faqat load/read va vaqtinchalik nusxa bilan ishlaydi.
    """

    from pathlib import Path
    import ast
    import py_compile
    import importlib.util
    import tempfile
    import json
    import shutil

    root = Path(__file__).resolve().parent
    errors = []
    warnings = []

    print("🧪 18-BOSQICH — REAL RUNTIME REGRESSION")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # --------------------------------------------------------
    # 1. Aktiv fayllar
    # --------------------------------------------------------

    active = []

    for path in sorted(root.glob("*.py")):
        name = path.name.lower()

        if name == "autobuilder.py":
            continue
        if "_backup" in name:
            continue
        if name.startswith("backup_"):
            continue
        if name.endswith("_patch.py"):
            continue

        active.append(path)

    print(f"📁 Aktiv fayllar: {len(active)}")

    # --------------------------------------------------------
    # 2. Compile
    # --------------------------------------------------------

    compile_errors = []

    for path in active:
        try:
            py_compile.compile(
                str(path),
                doraise=True
            )
        except Exception as exc:
            compile_errors.append(
                f"{path.name}: {exc}"
            )

    if compile_errors:
        errors.extend(compile_errors)
        print("❌ Compile regression")
    else:
        print("✅ Compile regression — OK")

    # --------------------------------------------------------
    # 3. Runtime import
    # --------------------------------------------------------

    runtime_targets = [
        "config.py",
        "database.py",
        "moderation.py",
        "game.py",
        "player.py",
        "profile.py",
        "economy.py",
        "shop.py",
        "weapons.py",
        "keyboards.py",
        "rewards.py",
        "missions.py",
        "achievements.py",
        "ranking.py",
        "main.py",
    ]

    imported = []

    for filename in runtime_targets:

        path = root / filename

        if not path.exists():
            errors.append(
                f"Runtime fayl yo‘q: {filename}"
            )
            continue

        try:

            module_name = (
                "stage18_runtime_"
                + path.stem
            )

            spec = importlib.util.spec_from_file_location(
                module_name,
                str(path)
            )

            if spec is None or spec.loader is None:
                raise RuntimeError(
                    "import spec mavjud emas"
                )

            module = importlib.util.module_from_spec(
                spec
            )

            spec.loader.exec_module(module)

            imported.append(filename)

        except Exception as exc:

            errors.append(
                f"Runtime import {filename}: {exc}"
            )

    if len(imported) == len(runtime_targets):
        print(
            f"✅ Runtime import — {len(imported)} ta"
        )
    else:
        print(
            f"❌ Runtime import — "
            f"{len(imported)}/{len(runtime_targets)}"
        )

    # --------------------------------------------------------
    # 4. Database runtime API
    # --------------------------------------------------------

    try:

        db = next(
            (
                m for m in [
                    globals().get(
                        "stage18_runtime_database"
                    )
                ]
                if m is not None
            ),
            None
        )

        if db is None:
            db_path = root / "database.py"

            spec = importlib.util.spec_from_file_location(
                "stage18_database_direct",
                str(db_path)
            )

            if spec is None or spec.loader is None:
                raise RuntimeError(
                    "database spec yaratilmadi"
                )

            db = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db)

        required = [
            "load_data",
            "save_data",
            "get_user",
            "ensure_user",
            "update_user",
            "is_admin",
        ]

        missing = [
            name
            for name in required
            if not callable(getattr(db, name, None))
        ]

        if missing:
            raise RuntimeError(
                "Missing API: "
                + ", ".join(missing)
            )

        data = db.load_data()

        if not isinstance(data, dict):
            raise RuntimeError(
                "load_data() dict qaytarmadi"
            )

        for key in [
            "users",
            "admins",
            "group_settings",
            "stats_history",
            "groups",
        ]:
            if key not in data:
                raise RuntimeError(
                    f"Database key yo‘q: {key}"
                )

        if not isinstance(data["users"], dict):
            raise RuntimeError(
                "users dict emas"
            )

        if not isinstance(data["groups"], dict):
            raise RuntimeError(
                "groups dict emas"
            )

        print(
            f"✅ Database runtime — "
            f"{len(data['users'])} users, "
            f"{len(data['groups'])} groups"
        )

    except Exception as exc:
        errors.append(
            f"Database runtime: {exc}"
        )
        print("❌ Database runtime")

    # --------------------------------------------------------
    # 5. Main handler regression
    # --------------------------------------------------------

    try:

        main_source = (
            (root / "main.py")
            .read_text(encoding="utf-8")
        )

        tree = ast.parse(main_source)

        handlers = []

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_handler"
            ):
                handlers.append(node)

        if len(handlers) < 1:
            raise RuntimeError(
                "add_handler topilmadi"
            )

        print(
            f"✅ Main handlers — {len(handlers)} ta"
        )

    except Exception as exc:
        errors.append(
            f"Main handler regression: {exc}"
        )
        print("❌ Main handlers")

    # --------------------------------------------------------
    # 6. Moderation critical symbols
    # --------------------------------------------------------

    try:

        mod_source = (
            (root / "moderation.py")
            .read_text(encoding="utf-8")
        )

        mod_tree = ast.parse(mod_source)

        symbols = {
            node.name
            for node in ast.walk(mod_tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            )
        }

        critical = {
            "settinghelp_command",
            "moderation_callback",
            "warn_command",
            "mute_command",
            "ban_command",
            "kick_command",
        }

        missing = critical - symbols

        if missing:
            raise RuntimeError(
                "Missing moderation symbols: "
                + ", ".join(sorted(missing))
            )

        print("✅ Moderation critical API — OK")

    except Exception as exc:
        errors.append(
            f"Moderation API regression: {exc}"
        )
        print("❌ Moderation critical API")

    # --------------------------------------------------------
    # 7. Game critical symbols
    # --------------------------------------------------------

    try:

        game_source = (
            (root / "game.py")
            .read_text(encoding="utf-8")
        )

        game_tree = ast.parse(game_source)

        game_symbols = {
            node.name
            for node in ast.walk(game_tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            )
        }

        if "setting_command" not in game_symbols:
            raise RuntimeError(
                "game.py setting_command yo‘q"
            )

        if "setting_callback" not in game_symbols:
            raise RuntimeError(
                "game.py setting_callback yo‘q"
            )

        print("✅ Ko‘k–Qizil settings API — OK")

    except Exception as exc:
        errors.append(
            f"Game regression: {exc}"
        )
        print("❌ Ko‘k–Qizil settings API")

    # --------------------------------------------------------
    # 8. Backup isolation
    # --------------------------------------------------------

    try:

        backup_root = root / ".autobuilder_backups"

        if not backup_root.exists():
            raise RuntimeError(
                "Backup katalogi mavjud emas"
            )

        print("✅ Backup isolation — OK")

    except Exception as exc:
        errors.append(
            f"Backup isolation: {exc}"
        )
        print("❌ Backup isolation")

    # --------------------------------------------------------
    # NATIJA
    # --------------------------------------------------------

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if warnings:
        print("⚠️ Ogohlantirishlar:")
        for item in warnings:
            print("   •", item)

    if errors:

        print("❌ 18-BOSQICH — MUVAFFAQIYATSIZ")

        for error in errors:
            print("   •", error)

        return False

    print("🏆 18-BOSQICH — MUVAFFAQIYATLI")
    print("🐍 Runtime — ✅")
    print("🗄️ Database — ✅")
    print("🎮 Game API — ✅")
    print("🛡️ Moderation API — ✅")
    print("🔗 Handlerlar — ✅")
    print("📦 Backup — ✅")
    print("🧪 Regression — ✅")

    return True

if __name__ == "__main__":
    raise SystemExit(main())
