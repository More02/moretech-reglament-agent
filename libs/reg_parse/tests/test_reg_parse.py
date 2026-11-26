from __future__ import annotations

from pathlib import Path

import docx
import pytest

from reg_parse import build_document, read_docx, read_html

REAL = Path(__file__).resolve().parents[3] / "data" / "regulations"


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    d = docx.Document()
    for line in [
        "Тестовый регламент",
        "1. Пресейл",
        "1.1. Заявка должна быть инициирована не менее чем за 3 рабочих дня до подачи.",
        "Важно: без анкеты заявка не берётся в работу.",
        "1.2. Бюджетная оценка не может использоваться для подачи в конкурс (за исключением RFI).",
        "2. Проект",
        "2.1. Работы без договора запрещены. См. п. 1.2 и п. 9.9.",
        "3 рабочих дня - это не номер пункта.",
        "2.1.1. Исключение - гарантийное письмо. Порядок - по регламенту подбора субподрядчика.",
    ]:
        d.add_paragraph(line)
    d.add_paragraph("Список документов", style="List Bullet")
    table = d.add_table(rows=3, cols=2)
    table.rows[0].cells[0].text = "Обязательно"
    table.rows[0].cells[1].text = "При наличии"
    table.rows[1].cells[0].text = "- ТКП;"
    table.rows[1].cells[1].text = "- Матрица ответственности;"
    table.rows[2].cells[0].text = "- Договор;"
    path = tmp_path / "sample.docx"
    d.save(str(path))
    return path


def test_builds_clause_tree(sample_docx: Path) -> None:
    doc = build_document("t", read_docx(sample_docx))
    assert doc.title == "Тестовый регламент"
    assert [c.number for c in doc.clauses] == ["1", "1.1", "1.2", "2", "2.1", "2.1.1"]
    c11 = doc.clause("1.1")
    assert c11 is not None
    assert c11.parent == "1"
    assert c11.path == ("1. Пресейл",)
    assert "Важно: без анкеты" in c11.text
    c211 = doc.clause("2.1.1")
    assert c211 is not None
    assert c211.path == ("2. Проект", "2.1. Работы без договора запрещены. См. п. 1.2 и п. 9.9.")


def test_number_without_dot_is_not_a_section(sample_docx: Path) -> None:
    doc = build_document("t", read_docx(sample_docx))
    c21 = doc.clause("2.1")
    assert c21 is not None
    assert "3 рабочих дня - это не номер пункта." in c21.text


def test_table_is_read_by_columns(sample_docx: Path) -> None:
    doc = build_document("t", read_docx(sample_docx))
    last = doc.clauses[-1]
    assert "Обязательно:\n• ТКП;\n• Договор;\nПри наличии:\n• Матрица ответственности;" in last.text


def test_references_detect_missing_clause_and_documents(sample_docx: Path) -> None:
    doc = build_document("t", read_docx(sample_docx))
    clause_refs = {(r.target, r.exists) for r in doc.references if r.kind == "clause"}
    assert ("1.2", True) in clause_refs
    assert ("9.9", False) in clause_refs
    doc_refs = {r.target for r in doc.references if r.kind == "document"}
    assert "регламент подбора субподрядчика" in doc_refs


def test_fingerprint_changes_with_text(sample_docx: Path) -> None:
    doc = build_document("t", read_docx(sample_docx))
    paras = read_docx(sample_docx)
    changed = [p if "3 рабочих дня до" not in p.text else type(p)(text=p.text.replace("3", "5", 1)) for p in paras]
    doc2 = build_document("t", changed)
    assert doc.clause("1.1").fingerprint != doc2.clause("1.1").fingerprint  # type: ignore[union-attr]
    assert doc.clause("1.2").fingerprint == doc2.clause("1.2").fingerprint  # type: ignore[union-attr]


def test_html_reader_for_confluence_pages() -> None:
    page = "<h1>Регламент</h1><p>1. Раздел</p><p>1.1. Пункт &laquo;А&raquo;</p><ul><li>перечисление</li></ul>"
    doc = build_document("h", read_html(page))
    assert doc.title == "Регламент"
    c = doc.clause("1.1")
    assert c is not None
    assert c.text == "Пункт «А»\n• перечисление"


@pytest.mark.skipif(not REAL.exists(), reason="корпус заказчика монтируется отдельно и в репозиторий не входит")
def test_real_corpus_known_facts() -> None:
    ib_presale = build_document("ib-presale", read_docx(REAL / "Пресейловая деятельность Дирекции ИБ.docx"))
    dangling = [r for r in ib_presale.references if r.kind == "clause" and r.exists is False]
    assert any(r.target == "1.6" and r.clause_id == "ib-presale:7.2" for r in dangling)
    dbrct = build_document("dbrct-project", read_docx(REAL / "Проектная деятельность ДБРЦТ.docx"))
    c = dbrct.clause("2.4")
    assert c is not None
    assert "за исключением RFI" in c.text
