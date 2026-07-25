from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_settings_resolve_relative_paths_from_repo_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("careerpilot.backend.config", None)

    import careerpilot.backend.config as config_module

    importlib.reload(config_module)
    settings = config_module.get_settings()

    assert settings.sqlite_path.is_absolute()
    assert settings.chroma_path.is_absolute()
    assert settings.checkpoint_path.is_absolute()
