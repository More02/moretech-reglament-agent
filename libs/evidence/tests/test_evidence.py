from evidence import find_quote, numbers, verify_claim

CLAUSE = (
    "Заявка должна быть инициирована не менее чем за 3 рабочих дня до подачи предложения Заказчику. "
    "При невыполнении сроков Заявка отклоняется."
)


def test_exact_quote_with_typography_differences() -> None:
    m = find_quote("заявка должна быть инициирована не менее чем за 3 рабочих дня", CLAUSE)
    assert m is not None
    assert m.exact


def test_quote_with_small_typo_is_accepted() -> None:
    m = find_quote("Заявка должна быть инициированна не менее чем за 3 рабочих дня", CLAUSE)
    assert m is not None
    assert not m.exact


def test_invented_quote_is_rejected() -> None:
    assert find_quote("Заявка должна быть инициирована за 2 недели до подачи конкурса", CLAUSE) is None


def test_too_short_quote_proves_nothing() -> None:
    assert find_quote("Заявка", CLAUSE) is None


def test_numbers_digits_and_words_ignore_clause_numbers() -> None:
    assert numbers("за две недели, см. п. 8.4, не позднее 12 рабочих часов") == {"2", "12"}
    assert numbers("в течение трёх рабочих дней") == {"3"}


def test_claim_with_wrong_number_fails() -> None:
    check = verify_claim(
        "Заявку нужно инициировать минимум за 5 рабочих дней.",
        "не менее чем за 3 рабочих дня до подачи предложения",
        CLAUSE,
    )
    assert not check.ok
    assert check.unsupported_numbers == {"5"}


def test_claim_supported() -> None:
    check = verify_claim(
        "Заявку нужно создать не позже чем за три рабочих дня до подачи предложения.",
        "не менее чем за 3 рабочих дня до подачи предложения",
        CLAUSE,
    )
    assert check.ok


def test_texts_differ() -> None:
    from evidence import texts_differ

    assert not texts_differ(
        "Анкетирование проводит менеджер по качеству.", "За анкетирование отвечает менеджер по качеству."
    )
    assert texts_differ("Обновлять раз в неделю, 1 раз.", "Обновлять раз в месяц, 1 раз в 30 дней.")
    assert texts_differ(
        "РП обновляет реестр рисков не реже 1 раза в неделю.", "РП обновляет реестр рисков не реже 1 раза в месяц."
    )
    assert texts_differ("Подавать бюджетную оценку в конкурс нельзя.", "Подавать бюджетную оценку в конкурс можно.")
    assert texts_differ(
        "Анкетирование проводит менеджер по качеству.",
        "Анкетирование запускается автоматически при закрытии карточки проекта в CRM.",
    )
