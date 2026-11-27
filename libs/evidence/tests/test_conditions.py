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
