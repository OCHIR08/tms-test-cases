#!/usr/bin/env python3
"""Validate a JSON test case against schemas/test-case.schema.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "test-case.schema.json"


def format_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return f"- '{path}' {error.message}"
    return f"- {error.message}"


def load_json(path: Path, *, kind: str) -> object:
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        print(
            f"❌ ERROR: Файл '{path}' не является корректным JSON "
            f"(строка {exc.lineno}, колонка {exc.colno}): {exc.msg}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as exc:
        print(f"❌ ERROR: Не удалось прочитать {kind} '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Валидация JSON тест-кейса по схеме test-case.schema.json",
    )
    parser.add_argument("json_path", help="Путь к JSON-файлу тест-кейса")
    args = parser.parse_args()

    test_case_path = Path(args.json_path)

    if not SCHEMA_PATH.is_file():
        print(
            f"❌ ERROR: Схема не найдена: {SCHEMA_PATH}\n"
            "Ожидаемый путь относительно корня проекта: schemas/test-case.schema.json",
            file=sys.stderr,
        )
        return 1

    if not test_case_path.is_file():
        print(f"❌ ERROR: Файл не найден: {test_case_path}", file=sys.stderr)
        return 1

    schema = load_json(SCHEMA_PATH, kind="схему")
    instance = load_json(test_case_path, kind="тест-кейс")

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.absolute_path))

    if errors:
        print("❌ ERRORS FOUND:")
        for error in errors:
            print(format_error(error))
        return 1

    print("✅ VALID: Тест-кейс соответствует схеме")
    return 0


if __name__ == "__main__":
    sys.exit(main())
