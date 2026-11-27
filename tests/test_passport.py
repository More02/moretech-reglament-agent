from reglament_agent.config import ROOT
from reglament_agent.passport import Passport


def test_softline_passport_is_consistent() -> None:
    p = Passport.load(ROOT / "passports" / "softline.yaml")
    dep_ids = {d.id for d in p.departments}
    assert {d.department for d in p.documents} <= dep_ids
    assert any(g.canonical == "Запасные части, инструменты и принадлежности" for g in p.glossary)
    g = p.build_glossary()
    assert {t.canonical for t in g.find("Что делает PM и кто считает ТЗТ?")} >= {
        "Руководитель проекта",
        "Расчёт трудозатрат",
    }
    dbrct = p.document("dbrct-project")
    assert dbrct.process_of("2.4") == "presale"
    assert dbrct.process_of("8.4") == "project"
    assert p.document("ib-presale").process_of("7.2") == "presale"
