#!/usr/bin/env python3
"""Validate all JSON test cases under examples/ against test-case.schema.json."""

from __future__ import annotations

import sys
from pathlib import Path

from validate_tc import (
    PROJECT_ROOT,
    collect_schema_errors,
    create_validator,
    try_load_json,
)

EXAMPLES_DIR = PROJECT_ROOT / "examples"


def find_json_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.json"))


def validate_file(path: Path, validator) -> list[str]:
    instance, load_error = try_load_json(path)
    if load_error:
        return [f"- {load_error}"]
    return collect_schema_errors(instance, validator)


def main() -> int:
    if not EXAMPLES_DIR.is_dir():
        print(f"❌ ERROR: Папка не найдена: {EXAMPLES_DIR}", file=sys.stderr)
        return 1

    json_files = find_json_files(EXAMPLES_DIR)
    if not json_files:
        print(f"❌ ERROR: JSON-файлы не найдены в {EXAMPLES_DIR}", file=sys.stderr)
        return 1

    validator = create_validator()
    valid_files: list[Path] = []
    invalid_files: list[tuple[Path, list[str]]] = []

    for path in json_files:
        errors = validate_file(path, validator)
        if errors:
            invalid_files.append((path, errors))
        else:
            valid_files.append(path)

    print("✅ Валидные файлы:")
    if valid_files:
        for path in valid_files:
            print(f"- {path.relative_to(PROJECT_ROOT)}")
    else:
        print("- нет")

    print()
    print("❌ Невалидные файлы:")
    if invalid_files:
        for path, errors in invalid_files:
            print(f"- {path.relative_to(PROJECT_ROOT)}")
            for error in errors:
                print(f"  {error}")
    else:
        print("- нет")

    print()
    print("Статистика:")
    print(f"- Всего файлов: {len(json_files)}")
    print(f"- Валидных: {len(valid_files)}")
    print(f"- Невалидных: {len(invalid_files)}")

    return 0 if not invalid_files else 1


if __name__ == "__main__":
    sys.exit(main())
