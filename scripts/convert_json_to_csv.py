#!/usr/bin/env python3
"""Convert draft JSON test cases to TMS CSV (semicolon, UTF-8-sig)."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFT_DIR = PROJECT_ROOT / "draft"
OUTPUT_PATH = PROJECT_ROOT / "output" / "tms_import.csv"
TEMPLATE_PATH = PROJECT_ROOT / "cases-template.csv"

SKIP_IDS = {41, 47, 730} | set(range(242, 251))
CASE_ID_RE = re.compile(r"NAVI2E-(\d+)", re.IGNORECASE)
LEGACY_RE = re.compile(
    r"статус\s*=\s*(?P<status>\w+)\s*,\s*серьезность\s*=\s*(?P<severity>\w+)",
    re.IGNORECASE,
)

CSV_COLUMNS = [
    "Название",
    "Описание",
    "Предусловие",
    "Приоритет",
    "Критичность",
    "Статус",
    "Тип",
    "Слой",
    "Теги",
    "Шаги",
]

PRIORITY_MAP = {
    "Critical": "критический",
    "High": "высокий",
    "Medium": "средний",
    "Low": "низкий",
}

SEVERITY_MAP = {
    "Critical": "critical",
    "Major": "major",
    "Minor": "minor",
}

STATUS_MAP = {
    "Actual": "актуальный",
    "Draft": "черновик",
    "Obsolete": "устаревший",
}

TYPE_MAP = {
    "positive": "smoke",
    "negative": "functional",
    "edge_case": "functional",
}


def parse_case_number(case_id: str, filename: str) -> int | None:
    match = CASE_ID_RE.search(case_id) or CASE_ID_RE.search(filename)
    return int(match.group(1)) if match else None


def skip_reason(case_num: int | None) -> str | None:
    if case_num is None:
        return "нет ID NAVI2E"
    if case_num in (41, 47):
        return "Obsolete"
    if 242 <= case_num <= 250:
        return "ПФДОД"
    if case_num == 730:
        return "Соц.заказ"
    return None


def split_notes(notes: str) -> tuple[str, str, str]:
    """Return (description, legacy_status, legacy_severity)."""
    if not notes:
        return "", "", ""

    legacy_match = LEGACY_RE.search(notes)
    status = legacy_match.group("status") if legacy_match else ""
    severity = legacy_match.group("severity") if legacy_match else ""

    description = re.split(r"\nLegacy:", notes, maxsplit=1)[0].strip()
    if description.lower().startswith("legacy:"):
        description = ""
    return description, status, severity


def map_priority(raw: str) -> str:
    return PRIORITY_MAP.get(raw, "средний")


def map_severity(raw: str) -> str:
    return SEVERITY_MAP.get(raw, "major")


def map_status(raw: str) -> str:
    return STATUS_MAP.get(raw, "черновик")


def map_type(raw: str) -> str:
    return TYPE_MAP.get(raw, "functional")


def format_steps(steps: list[dict]) -> str:
    ordered = sorted(steps, key=lambda step: int(step.get("step_number") or 0))
    lines: list[str] = []
    for step in ordered:
        action = str(step.get("action", "")).strip()
        expected = str(step.get("expected_result", "")).strip()
        lines.append(f"{action} | {expected}")
    return "\n".join(lines)


def to_csv_row(payload: dict) -> dict[str, str]:
    case_id = str(payload.get("id", "")).strip()
    title = str(payload.get("title", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    description, legacy_status, legacy_severity = split_notes(notes)
    csv_type = map_type(str(payload.get("type", "")))
    module = str(payload.get("module", "")).strip()
    preconditions = payload.get("preconditions") or []

    return {
        "Название": f"{case_id}: {title}".strip(": "),
        "Описание": description or title,
        "Предусловие": "\n".join(str(item).strip() for item in preconditions if str(item).strip()),
        "Приоритет": map_priority(str(payload.get("priority", ""))),
        "Критичность": map_severity(legacy_severity),
        "Статус": map_status(legacy_status),
        "Тип": csv_type,
        "Слой": "e2e",
        "Теги": f"{module};{csv_type}" if module else csv_type,
        "Шаги": format_steps(payload.get("steps") or []),
    }


def load_header() -> list[str]:
    if TEMPLATE_PATH.is_file():
        with TEMPLATE_PATH.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, delimiter=";")
            header = next(reader, [])
            header = [cell.strip() for cell in header if cell.strip()]
            if header:
                return header
    return CSV_COLUMNS


def convert() -> int:
    if not DRAFT_DIR.is_dir():
        print(f"❌ ERROR: Папка не найдена: {DRAFT_DIR}", file=sys.stderr)
        return 1

    json_files = sorted(DRAFT_DIR.rglob("*.json"))
    if not json_files:
        print(f"❌ ERROR: JSON-файлы не найдены в {DRAFT_DIR}", file=sys.stderr)
        return 1

    header = load_header()
    rows: list[dict[str, str]] = []
    converted = 0
    skipped = 0
    skipped_details: list[str] = []

    for path in json_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            skipped += 1
            skipped_details.append(f"- {path.name}: некорректный JSON ({exc.msg})")
            continue

        if not isinstance(payload, dict):
            skipped += 1
            skipped_details.append(f"- {path.name}: ожидался объект JSON")
            continue

        case_id = str(payload.get("id", ""))
        case_num = parse_case_number(case_id, path.name)
        reason = skip_reason(case_num)
        if reason:
            skipped += 1
            skipped_details.append(f"- {case_id or path.name}: {reason}")
            continue

        rows.append(to_csv_row(payload))
        converted += 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=header,
            delimiter=";",
            extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in header})

    print(f"Конвертировано: {converted}")
    print(f"Пропущено: {skipped}")
    print(f"Файл: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    if skipped_details:
        print("Пропущенные кейсы:")
        print("\n".join(skipped_details))
    return 0


if __name__ == "__main__":
    sys.exit(convert())
