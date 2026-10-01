# ⚠️ CRITICAL RULES & BOUNDARIES

**MANDATORY TRIGGER**: Применяй эти правила ТОЛЬКО если пользователь явно просит создать, обновить или проанализировать TMS тест-кейс (Test Case) для ручного тестирования системы Навигатор дополнительного образования.

**DO NOT USE IF**: 
- Пользователь просит написать баг-репорт (Bug Report)
- Пользователь просит написать Unit-тест или код автоматизации
- Задача не связана с модулями: registration, authorization, programs, cabinet, activities, news

**FORBIDDEN**: 
- Никогда не используй примеры из папки `examples-legacy/`
- Никогда не генерируй тест-кейсы без секций: Preconditions, Steps, Expected Result

---
# Project rules for Roo Code

## Scope
- Use these rules for all generated QA test cases in this repository.
- Prefer the repository template in `templates/case-template.md`.
- Store new cases in the `examples/` folder unless the task explicitly says otherwise.

## Writing style
- Write in Russian unless the task explicitly requests English.
- Use imperative mood: "Перейти", "Нажать", "Заполнить".
- Keep every step as one action and one expected result.
- Add a screenshot for each step when possible.
- Keep the wording concise and testable.

## Naming and structure
- Use IDs in the format `TC-XXX` or `NAVI2E-XXX` depending on the project convention.
- Include sections: Description, Preconditions, Steps, Overall expected result, Parameters, Screenshots.
- Use the template structure from `templates/case-template.md` as the default layout.

## Test-case types
1. Positive scenarios
2. Negative validation scenarios
3. Boundary and edge cases

## Priorities
- Critical: core user journeys such as registration, authorization, submission
- High: important features such as catalog, personal cabinet
- Medium: search, filters, secondary flows
- Low: UI/UX details

## Environment and data
- Use URLs in the format `https://www.{СТЕНД}.navi.inlearno.info`.
- Replace `{СТЕНД}` with the target environment name.
- Use test data generated from `https://randomdatatools.ru/`.
- Prefer email format `test+{число}@example.com`.
- Use password values with at least 8 characters, including letters and numbers.

## Required checks
- Verify required fields and validation messages.
- Check XSS/unsafe input handling where text fields are involved.
- Validate success, error, and boundary states.
- Mention browser/mobile readability when relevant.
- Add explicit acceptance criteria when the scenario is complex.

## Output rules
- Do not invent screenshots that do not exist in the repository.
- If a screenshot is needed, reference the existing folder structure under `screenshots/`.
- Keep data-driven tables structured and readable.
- Prefer markdown headings and short sections over long narrative blocks.
