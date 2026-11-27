from evidence import full_sentence, lost_condition

RULE = (
    "РП может привлечь субподрядчика к выполнению работ только после подписания субподрядного договора "
    "и при наличии Заказа покупателя в учётной системе, по которому пришла оплата или согласована КИ."
)
BAN = (
    "Работы без подписанного договора и согласованной сметы запрещены. "
    "Исключение – наличие гарантийного письма Заказчика и письменное согласование Директора направления."
)


def test_second_condition_lost() -> None:
    rest = lost_condition("РП может привлечь субподрядчика к выполнению работ только после подписания", RULE)
    assert rest is not None
    assert "заказа покупателя" in rest


def test_full_rule_is_complete() -> None:
    assert lost_condition(RULE, RULE) is None


def test_exception_sentence_lost() -> None:
    assert lost_condition("Работы без подписанного договора и согласованной сметы запрещены", BAN)


def test_exception_covered_by_other_claim() -> None:
    other = ["Исключение – наличие гарантийного письма Заказчика и письменное согласование Директора направления"]
    assert lost_condition("Работы без подписанного договора и согласованной сметы запрещены", BAN, other) is None


def test_plain_fact_not_flagged() -> None:
    text = "Ресурс-менеджер определяет компетенции, объём работ и назначает ГИП. Срок назначения – 1 рабочий день."
    assert lost_condition("Ресурс-менеджер определяет компетенции", text) is None


def test_full_sentence_keeps_exception() -> None:
    assert full_sentence("Работы без подписанного договора", BAN) == BAN


def test_condition_dropped_from_claim_text() -> None:
    from evidence import dropped_condition

    claim = "РП может привлечь субподрядчика только после подписания субподрядного договора."
    assert dropped_condition(claim, RULE)
    full = claim[:-1] + " и при наличии оплаченного Заказа покупателя в учётной системе."
    assert dropped_condition(full, RULE) is None


def test_week_instead_of_month_is_rejected() -> None:
    from evidence import verify_claim

    text = "РП актуализирует реестр рисков не реже одного раза в месяц."
    assert not verify_claim("Реестр рисков обновляется не реже раза в неделю.", text, text).ok
    assert verify_claim("Реестр рисков обновляется ежемесячно.", text, text).ok
