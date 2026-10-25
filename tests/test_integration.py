from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dsh_property_lab import __version__
from dsh_property_lab.integration import install_dsh


def test_install_into_home_with_spaces_and_run_pinned_doctor(tmp_path):
    home = tmp_path / "DSH home with spaces"
    target_project = tmp_path / "unrelated target project"
    target_project.mkdir()
    target = install_dsh(home)

    assert target == home / "skills" / "dsh-property-lab"
    runtime = json.loads((target / "runtime.json").read_text(encoding="utf-8"))
    assert Path(runtime["python"]).resolve() == Path(sys.executable).resolve()
    assert runtime["version"] == __version__
    assert (target / "references" / "spec-format.md").is_file()

    env = dict(os.environ, DSH_HOME=str(home))
    completed = subprocess.run(
        [sys.executable, str(target / "scripts" / "run.py"), "doctor"],
        cwd=target_project, env=env, capture_output=True, text=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["dsh_skill_installed"] is True
    assert Path(result["dsh_home"]).resolve() == home.resolve()
    assert Path(result["executable"]).resolve() == Path(sys.executable).resolve()
    assert result["model_api_used"] is False
    assert not (target_project / ".dsh").exists()


def test_reinstall_refreshes_managed_files_without_stacking_runtime(tmp_path):
    home = tmp_path / "DSH home"
    target = install_dsh(home)
    original = (target / "SKILL.md").read_text(encoding="utf-8")
    (target / "SKILL.md").write_text(original + "\nSTALE GENERATED CONTENT\n", encoding="utf-8")
    (target / "references" / "spec-format.md").write_text("stale", encoding="utf-8")
    installed_again = install_dsh(home)

    assert installed_again == target
    current = (target / "SKILL.md").read_text(encoding="utf-8")
    assert current == original
    assert current.count("## Installed runtime") == 1
    assert (target / "references" / "spec-format.md").read_text(encoding="utf-8") != "stale"
    marker = json.loads((target / ".property-lab-managed.json").read_text(encoding="utf-8"))
    assert marker == {"owner": "dsh-property-lab", "version": __version__}


def test_unmanaged_skill_directory_is_preserved(tmp_path):
    home = tmp_path / "DSH home"
    target = home / "skills" / "dsh-property-lab"
    target.mkdir(parents=True)
    existing = b"A user's existing skill\r\n"
    (target / "SKILL.md").write_bytes(existing)

    with pytest.raises(ValueError, match="unmanaged skill directory"):
        install_dsh(home)

    assert (target / "SKILL.md").read_bytes() == existing
    assert sorted(item.name for item in target.iterdir()) == ["SKILL.md"]


def test_runner_reports_removed_pinned_environment(tmp_path):
    home = tmp_path / "DSH home"
    target = install_dsh(home)
    (target / "runtime.json").write_text(
        json.dumps({"python": str(tmp_path / "missing environment" / "python"), "version": __version__}),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(target / "scripts" / "run.py"), "doctor"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert completed.returncode == 2
    assert "Re-run install-dsh" in completed.stderr


@pytest.mark.parametrize("marker", ['not json', '{"owner":"another-tool"}', '[]'])
def test_invalid_ownership_marker_is_preserved(tmp_path, marker):
    home = tmp_path / "DSH home"
    target = home / "skills" / "dsh-property-lab"
    target.mkdir(parents=True)
    sentinel = target / ".property-lab-managed.json"
    sentinel.write_text(marker, encoding="utf-8")
    with pytest.raises(ValueError, match="unmanaged"):
        install_dsh(home)
    assert sentinel.read_text(encoding="utf-8") == marker
