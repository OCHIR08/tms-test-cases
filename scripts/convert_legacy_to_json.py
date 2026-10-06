#!/usr/bin/env python3
"""Convert legacy Markdown test cases to JSON files matching test-case.schema.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = PROJECT_ROOT / "examples-legacy" / "test-case-legacy-site.md"
OUTPUT_DIR = PROJECT_ROOT / "examples"

SKIP_IDS = {41, 47, 730} | set(range(242, 251))

CASE_HEADER_RE = re.compile(r"^# (NAVI2E-(\d+)):\s*(.+?)\s*$", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|")
STEP_RE = re.compile(
    r"\*\*(\d+)\.\s*Действие:\*\*\s*(.*?)\n\s*>\s*\*\*Ожидаемый результат:\*\*\s*(.*?)(?=\n\*\*\d+\.\s*Действие:|\Z)",
    re.DOTALL,
)

SECTION_HEADINGS = {
    "description": r"##\s*📝\s*Описание",
    "preconditions": r"##\s*⚠️\s*Предусловия",
    "expected_result": r"##\s*🎯\s*Ожидаемый результат",
    "steps": r"##\s*👣\s*Шаги выполнения",
}

PRIORITY_MAP = {
    "Critical": "Critical",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
}

TYPE_MAP = {
    "Smoke": "positive",
    "Other": "positive",
    "Functional": "negative",
}

TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def collapse_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def normalize_block(text: str) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
    cleaned = re.sub(r"(?:\s*^---+\s*)+$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^---+\s*", "", cleaned)
    return cleaned.strip()


def extract_section(body: str, heading_re: str) -> str:
    pattern = re.compile(
        rf"{heading_re}\s*\n(.*?)(?=\n##\s|\Z)",
        re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return ""
    return normalize_block(match.group(1))


def parse_table(body: str) -> dict[str, str]:
    params: dict[str, str] = {}
    table_match = re.search(r"\| Параметр \| Значение \|.*?(?=\n## |\Z)", body, re.DOTALL)
    table_text = table_match.group(0) if table_match else body
    for key, value in TABLE_ROW_RE.findall(table_text):
        params[key.strip()] = collapse_ws(value)
    return params


def split_preconditions(raw: str) -> list[str]:
    if not raw:
        return []

    parts = [collapse_ws(line) for line in raw.splitlines() if collapse_ws(line)]
    if len(parts) > 1:
        return parts

    text = parts[0] if parts else collapse_ws(raw)
    split = re.split(r"(?<=[.!?])\s+(?=[А-ЯA-Z])", text)
    items = [collapse_ws(item) for item in split if collapse_ws(item)]
    return items or [text]


def parse_steps(raw: str) -> list[dict]:
    steps: list[dict] = []
    for number, action, expected in STEP_RE.findall(raw):
        action_text = collapse_ws(re.sub(r"-{3,}", " ", action.replace("\n", " ")))
        expected_text = collapse_ws(re.sub(r"-{3,}", " ", expected.replace("\n", " ")))
        if len(action_text) < 5:
            action_text = f"{action_text} (шаг)"
        if len(expected_text) < 5:
            expected_text = f"{expected_text} (см. шаг)"
        steps.append(
            {
                "step_number": int(number),
                "action": action_text,
                "expected_result": expected_text,
            }
        )
    return steps


def resolve_module(case_id: int) -> str | None:
    if case_id in (1, 8):
        return "registration"
    if case_id in (6, 7):
        return "authorization"
    if case_id in (2, 4, 5, 727, 745, 746):
        return "cabinet"
    if 37 <= case_id <= 47 or case_id in (713, 714):
        return "programs"
    if 193 <= case_id <= 200 or case_id == 811 or 851 <= case_id <= 857:
        return "activities"
    if 423 <= case_id <= 427 or case_id in (441, 442):
        return "news"
    return None


def skip_reason(case_id: int) -> str | None:
    if case_id in (41, 47):
        return "Obsolete"
    if 242 <= case_id <= 250:
        return "ПФДОД"
    if case_id == 730:
        return "Соц.заказ"
    if resolve_module(case_id) is None:
        return "нет маппинга модуля"
    return None


def slugify(title: str, max_len: int = 50) -> str:
    lowered = title.lower()
    chars: list[str] = []
    for char in lowered:
        if char in TRANSLIT:
            chars.append(TRANSLIT[char])
        elif char.isascii() and (char.isalnum() or char in "-_"):
            chars.append(char)
        else:
            chars.append("-")
    slug = re.sub(r"-+", "-", "".join(chars)).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug or "case"


def map_priority(raw: str) -> str:
    return PRIORITY_MAP.get(raw, "Medium")


def map_type(raw: str) -> str:
    return TYPE_MAP.get(raw, "positive")


def split_cases(markdown: str) -> list[tuple[str, int, str, str]]:
    headers = list(CASE_HEADER_RE.finditer(markdown))
    cases: list[tuple[str, int, str, str]] = []
    for index, match in enumerate(headers):
        case_id_str = match.group(1)
        case_num = int(match.group(2))
        title = collapse_ws(match.group(3)).rstrip(".")
        start = match.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(markdown)
        body = markdown[start:end]
        cases.append((case_id_str, case_num, title, body))
    return cases


def to_json_case(case_id: str, case_num: int, title: str, body: str) -> dict:
    params = parse_table(body)
    description = extract_section(body, SECTION_HEADINGS["description"])
    preconditions_raw = extract_section(body, SECTION_HEADINGS["preconditions"])
    expected_raw = extract_section(body, SECTION_HEADINGS["expected_result"])
    steps_raw = extract_section(body, SECTION_HEADINGS["steps"])
    steps = parse_steps(steps_raw)

    if expected_raw:
        expected_result = collapse_ws(re.sub(r"-{3,}", " ", expected_raw.replace("\n", " ")))
    elif description:
        expected_result = collapse_ws(description.replace("\n", " "))
    elif steps:
        expected_result = steps[-1]["expected_result"]
    else:
        expected_result = "Ожидаемый результат не указан в исходном кейсе"

    payload = {
        "id": case_id,
        "module": resolve_module(case_num),
        "priority": map_priority(params.get("Приоритет", "")),
        "type": map_type(params.get("Тип", "")),
        "title": title if len(title) >= 10 else f"{title} (legacy)",
        "preconditions": split_preconditions(preconditions_raw),
        "steps": steps,
        "expected_result": expected_result,
    }

    notes_parts = []
    if description:
        notes_parts.append(description)
    status = params.get("Статус")
    severity = params.get("Серьезность")
    if status or severity:
        notes_parts.append(
            collapse_ws(f"Legacy: статус={status or '—'}, серьезность={severity or '—'}")
        )
    if notes_parts:
        payload["notes"] = "\n".join(notes_parts)

    return payload


def convert() -> int:
    if not SOURCE_PATH.is_file():
        print(f"❌ ERROR: Исходный файл не найден: {SOURCE_PATH}", file=sys.stderr)
        return 1

    markdown = SOURCE_PATH.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0
    skipped_details: list[str] = []
    written: list[str] = []

    for case_id, case_num, title, body in split_cases(markdown):
        reason = skip_reason(case_num)
        if reason:
            skipped += 1
            skipped_details.append(f"- {case_id}: {reason}")
            continue

        payload = to_json_case(case_id, case_num, title, body)
        if not payload["steps"]:
            skipped += 1
            skipped_details.append(f"- {case_id}: не удалось распарсить шаги")
            continue

        filename = f"{case_id}-{slugify(title)}.json"
        output_path = OUTPUT_DIR / filename
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        converted += 1
        written.append(str(output_path.relative_to(PROJECT_ROOT)))

    print(f"Конвертировано: {converted}")
    print(f"Пропущено: {skipped}")
    if skipped_details:
        print("Пропущенные кейсы:")
        print("\n".join(skipped_details))
    print("Записанные файлы:")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    sys.exit(convert())
