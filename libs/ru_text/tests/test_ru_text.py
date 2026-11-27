from ru_text import Glossary, Term, lemmas, normalize

GLOSSARY = Glossary(
    [
        Term("Руководитель проекта", ("РП", "PM", "проджект-менеджер", "проджект менеджер")),
        Term("Пресейл-архитектор", ("ПА", "архитектор пресейла")),
        Term("Расчёт трудозатрат", ("РТЗ", "ТЗТ")),
    ]
)


def test_normalize() -> None:
    assert normalize("  «Ёлка» —  тест ") == '"елка" - тест'


def test_lemmas_drop_stopwords() -> None:
    assert lemmas("Кто назначает руководителей проектов?") == ["назначать", "руководитель", "проект"]


def test_abbreviations_respect_case_and_word_boundaries() -> None:
    names = {t.canonical for t in GLOSSARY.find("Кто назначает РП и что делает ПА?")}
    assert names == {"Руководитель проекта", "Пресейл-архитектор"}
    assert GLOSSARY.find("положи в папку") == []


def test_inflected_synonym_is_found() -> None:
    names = {t.canonical for t in GLOSSARY.find("что должен сделать проджект-менеджеру")}
    assert "Руководитель проекта" in names


def test_expand_adds_canonical_names_once() -> None:
    assert GLOSSARY.expand("Срок РТЗ") == "Срок РТЗ (Расчёт трудозатрат)"
    assert GLOSSARY.expand("Срок расчёта трудозатрат РТЗ") == "Срок расчёта трудозатрат РТЗ"


def test_participles_are_reduced_to_infinitive() -> None:
    assert "инициировать" in lemmas("Заявка должна быть инициирована")
    assert "согласовать" in lemmas("без согласованной сметы")
