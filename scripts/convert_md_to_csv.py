#!/usr/bin/env python3
"""Convert Markdown test cases from cases/ to TMS CSV (semicolon, UTF-8-sig)."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = PROJECT_ROOT / "cases"
OUTPUT_PATH = PROJECT_ROOT / "output" / "tms_import_md.csv"

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
    "critical": "высокий",
    "high": "высокий",
    "medium": "средний",
    "low": "низкий",
}

TYPE_MAP = {
    "smoke": "smoke",
    "other": "functional",
    "functional": "functional",
}

REGISTRATION_AUTH = {1, 2, 3, 4, 5, 6, 9}
PROGRAMS = {7, 8, 10, 37, 39, 40, 42, 43, 44, 45, 442, 713, 714, 851, 852}
ACTIVITIES = set(range(193, 200)) | {200, 811} | set(range(853, 858))
NEWS = set(range(423, 428))
CABINET = {727, 745, 746}

CASE_ID_RE = re.compile(r"NAVI2E-(\d+)", re.IGNORECASE)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
STEP_RE = re.compile(r"^###\s+Шаг\s+(\d+)\s*$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LABEL_RE = re.compile(
    r"\*\*(Действие|Ожидаемый результат):\*\*\s*(.*?)(?=\n\*\*|\n###|\n##|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def module_for(case_num: int | None, path: Path) -> str:
    name = path.name.lower()
    if case_num == 4 and "program" in name:
        return "programs"
    if case_num == 4 and "user" in name:
        return "cabinet"
    if case_num in REGISTRATION_AUTH:
        return "registration/authorization"
    if case_num in PROGRAMS:
        return "programs"
    if case_num in ACTIVITIES:
        return "activities"
    if case_num in NEWS:
        return "news"
    if case_num in CABINET:
        return "cabinet"
    if "program" in name or "schedule" in name:
        return "programs"
    if "activit" in name:
        return "activities"
    if "blog" in name or "news" in name:
        return "news"
    if any(token in name for token in ("cabinet", "child", "user", "navigator", "snils")):
        return "cabinet"
    return "other"


def map_priority(raw: str) -> str:
    return PRIORITY_MAP.get(raw.strip().lower(), "высокий")


def case_type(description: str, title: str) -> str:
    text = f"{title}\n{description}".lower()
    if "негатив" in text:
        return "functional"
    return "smoke"


def clean_text(raw: str) -> str:
    without_images = IMAGE_RE.sub("", raw)
    lines = []
    for line in without_images.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("!["):
            continue
        lines.append(stripped)
    return " ".join(lines).strip()


def section_body(text: str, title: str) -> str:
    matches = list(SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip().lower() != title.lower():
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[start:end].strip()
    return ""


def preconditions(raw: str) -> str:
    items: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        if stripped:
            items.append(stripped)
    return "\n".join(items)


def labeled_blocks(step_body: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in LABEL_RE.finditer(step_body):
        label = match.group(1).strip().lower()
        found[label] = clean_text(match.group(2))
    return found


def parse_steps(steps_raw: str) -> list[tuple[int, str]]:
    matches = list(STEP_RE.finditer(steps_raw))
    steps: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(steps_raw)
        labels = labeled_blocks(steps_raw[start:end])
        action = labels.get("действие", "")
        expected = labels.get("ожидаемый результат", "")
        if not action and not expected:
            continue
        steps.append((number, f"{action} | {expected}"))
    steps.sort(key=lambda item: item[0])
    return steps


def parse_case(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    heading = H1_RE.search(text)
    if not heading:
        raise ValueError("нет заголовка первого уровня")

    title = heading.group(1).strip()
    id_match = CASE_ID_RE.search(title) or CASE_ID_RE.search(path.name)
    if not id_match:
        raise ValueError("нет ID NAVI2E")

    case_num = int(id_match.group(1))
    if not title.upper().startswith("NAVI2E-"):
        title = f"NAVI2E-{case_num:03d}: {title}"

    description = clean_text(section_body(text, "Описание")) or title
    precondition = preconditions(section_body(text, "Предусловия"))
    steps = parse_steps(section_body(text, "Шаги"))
    if not steps:
        raise ValueError("нет шагов")

    csv_type = case_type(description, title)
    module = module_for(case_num, path)
    priority_raw = clean_text(section_body(text, "Приоритет"))
    return {
        "Название": title,
        "Описание": description,
        "Предусловие": precondition,
        "Приоритет": map_priority(priority_raw),
        "Критичность": "critical" if csv_type == "smoke" else "major",
        "Статус": "актуальный",
        "Тип": TYPE_MAP.get(csv_type, "functional"),
        "Слой": "e2e",
        "Теги": f"{module};{csv_type}",
        "Шаги": "\n".join(line for _, line in steps),
    }


def convert() -> int:
    if not CASES_DIR.is_dir():
        print(f"ERROR: Папка не найдена: {CASES_DIR}", file=sys.stderr)
        return 1

    md_files = sorted(CASES_DIR.glob("*.md"))
    if not md_files:
        print(f"ERROR: Markdown-файлы не найдены в {CASES_DIR}", file=sys.stderr)
        return 1

    rows: list[dict[str, str]] = []
    warnings: list[str] = []

    for path in md_files:
        try:
            rows.append(parse_case(path))
        except (OSError, UnicodeError, ValueError) as exc:
            warnings.append(f"- {path.name}: {exc}")

    rows.sort(key=lambda row: row["Название"])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_COLUMNS,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Конвертировано: {len(rows)}")
    print(f"Пропущено: {len(warnings)}")
    print(f"Файл: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    if warnings:
        print("Предупреждения:")
        print("\n".join(warnings))
    return 0


if __name__ == "__main__":
    sys.exit(convert())
