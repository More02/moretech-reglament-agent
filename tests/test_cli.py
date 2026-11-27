import json
from pathlib import Path

import pytest

from reglament_agent import cli
from reglament_agent.config import get_settings


def test_ingest_command_prints_report(
    app: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    del app  # фикстура готовит регламенты и паспорт в tmp_path
    monkeypatch.setenv("LLM_FAKE", "true")
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "hashing")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.sqlite'}")
    monkeypatch.setenv("PASSPORT_PATH", str(tmp_path / "passport.yaml"))
    monkeypatch.setenv("REGULATIONS_DIR", str(tmp_path / "regs"))
    get_settings.cache_clear()
    try:
        assert cli.main(["ingest"]) == 0
    finally:
        get_settings.cache_clear()
    report = json.loads(capsys.readouterr().out)
    assert report["documents"] == 2
