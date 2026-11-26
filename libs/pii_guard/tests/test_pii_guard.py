from pii_guard import PiiGuard


def test_masks_and_restores_contacts_and_names() -> None:
    guard = PiiGuard(name_finder=lambda _t: [])
    src = "Иванов И. И. просит ответ на ivanov@corp.ru, тел. +7 (912) 345-67-89. Копия Иванов И. И."
    res = guard.mask(src)
    assert "ivanov@corp.ru" not in res.text
    assert "+7 (912) 345-67-89" not in res.text
    assert "Иванов" not in res.text
    assert res.text.count("[ПЕРСОНА_1]") == 2
    assert res.unmask(res.text) == src


def test_disabled_guard_is_noop() -> None:
    res = PiiGuard(enabled=False).mask("a@b.ru")
    assert res.text == "a@b.ru"
    assert res.mapping == {}


def test_custom_name_finder() -> None:
    guard = PiiGuard(name_finder=lambda t: ["Юлия Чердакова"] if "Юлия" in t else [])
    res = guard.mask("Ответила Юлия Чердакова из службы качества")
    assert res.text == "Ответила [ПЕРСОНА_1] из службы качества"
