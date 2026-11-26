"""Разбор регламентов в дерево пунктов."""

from reg_parse.model import Clause, DocReference, ParsedDocument
from reg_parse.readers import Para, read_docx, read_html
from reg_parse.structure import build_document

__all__ = ["Clause", "DocReference", "Para", "ParsedDocument", "build_document", "read_docx", "read_html"]
