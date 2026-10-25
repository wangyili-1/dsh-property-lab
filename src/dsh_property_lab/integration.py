"""DSH integration through its public filesystem skill format."""
from __future__ import annotations

from importlib import resources
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import sys

import hypothesis

from . import __version__


def dsh_home() -> Path:
    return Path(os.environ.get("DSH_HOME", str(Path.home() / ".dsh"))).expanduser().resolve()


def doctor() -> dict:
    home = dsh_home()
    target = home / "skills" / "dsh-property-lab"
    return {"property_lab": __version__, "python": sys.version.split()[0], "executable": sys.executable,
            "hypothesis": hypothesis.__version__, "dsh_home": str(home),
            "dsh_skill_installed": (target / "SKILL.md").is_file(),
            "skill_path": str(target / "SKILL.md"), "model_api_used": False}


def example_directory() -> Path:
    checkout = Path(__file__).resolve().parents[2] / "examples"
    if (checkout / "roundtrip-buggy.json").is_file():
        return checkout
    dist = distribution("dsh-property-lab")
    for item in dist.files or []:
        if str(item).replace("\\", "/").endswith("share/dsh-property-lab/examples/roundtrip-buggy.json"):
            return Path(dist.locate_file(item)).resolve().parent
    raise FileNotFoundError("Demo fixtures are missing. Run from a complete source checkout or reinstall the wheel.")


def install_dsh(home: Path | None = None) -> Path:
    home = home.expanduser().resolve() if home else dsh_home()
    target = home / "skills" / "dsh-property-lab"
    marker = target / ".property-lab-managed.json"
    if target.exists():
        try:
            managed = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            managed = {}
        if not isinstance(managed, dict) or managed.get("owner") != "dsh-property-lab":
            raise ValueError(f"Refusing to overwrite an unmanaged skill directory: {target}")
    template = resources.files("dsh_property_lab").joinpath("resources", "skill")
    target.mkdir(parents=True, exist_ok=True)
    (target / "scripts").mkdir(exist_ok=True)
    for source, destination in [(template.joinpath("SKILL.md"), target / "SKILL.md"),
                                 (template.joinpath("references", "spec-format.md"), target / "references" / "spec-format.md"),
                                 (template.joinpath("scripts", "run.py"), target / "scripts" / "run.py")]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    runtime = {"python": sys.executable, "version": __version__}
    (target / "runtime.json").write_text(json.dumps(runtime, ensure_ascii=True, indent=2), encoding="utf-8")
    with (target / "SKILL.md").open("a", encoding="utf-8") as stream:
        stream.write("\n## Installed runtime\n\n")
        stream.write(f"Runner: `{target / 'scripts' / 'run.py'}`\n\n")
        stream.write(f"Pinned Python: `{sys.executable}`\n\n")
        stream.write("Use the runner below to preserve the current target-project working directory.\n\n")
        if os.name == "nt":
            quote = lambda s: "'" + str(s).replace("'", "''") + "'"
            stream.write(f"```powershell\n& {quote(sys.executable)} {quote(target / 'scripts' / 'run.py')} doctor\n```\n")
        else:
            import shlex
            stream.write(f"```sh\n{shlex.quote(sys.executable)} {shlex.quote(str(target / 'scripts' / 'run.py'))} doctor\n```\n")
    marker.write_text(json.dumps({"owner": "dsh-property-lab", "version": __version__}), encoding="utf-8")
    return target
