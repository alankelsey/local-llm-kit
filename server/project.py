"""Per-project configuration loader and helpers for the local-llm kit."""

import copy
import json
import os
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path

CONFIG_PATH = ".claude/local-llm.json"

DEFAULTS: dict = {
    "language": "TypeScript",
    "conventions": "AGENTS.md",
    "conventions_for": [".ts", ".tsx"],
    "conventions_skip": ["Workflow"],
    "codemap": {"roots": ["src"], "extensions": [".ts", ".tsx"], "exclude": [".test.", ".d.ts"]},
    "aliases": {"@/": "src/"},
    "checks": {"lint": "npm run -s lint", "typecheck": "npm run -s typecheck", "test": "npm run -s test --"},
    "default_checks": ["lint", "typecheck", "test"],
    "test_check": "test",
}


def _type_ok(value: object, default: object) -> bool:
    """Return True if *value* has the same broad type (str/list/dict) as *default*."""
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list)
    if isinstance(default, dict):
        return isinstance(value, dict)
    return type(value) is type(default)


def load_project(root: Path) -> dict:
    """Load per-project config from *root*/.claude/local-llm.json overlaid on DEFAULTS."""
    result = copy.deepcopy(DEFAULTS)

    try:
        raw = (root / CONFIG_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return result

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return result

    if not isinstance(data, dict):
        return result

    for key, value in data.items():
        if key == "codemap":
            # Special merge: each codemap sub-key replaces the default sub-key.
            if not isinstance(value, dict):
                continue  # wrong type → keep entire default codemap
            merged = copy.deepcopy(result["codemap"])
            for ck, cv in value.items():
                if ck in merged:
                    if _type_ok(cv, merged[ck]):
                        merged[ck] = cv
                    # else: type mismatch → keep default sub-key
                else:
                    merged[ck] = cv  # new key not in defaults → copy as-is
            result["codemap"] = merged
        elif key in DEFAULTS:
            if _type_ok(value, DEFAULTS[key]):
                result[key] = value
            # else: type mismatch → keep default
        else:
            # Key not present in DEFAULTS → copy as-is.
            result[key] = value

    return result


def check_command(project: dict, name: str, test_filter: list[str]) -> str:
    """Build the shell command for a named check, appending quoted filters to the test check."""
    cmd = project["checks"].get(name) or f"npm run -s {name}"
    if name == project["test_check"] and test_filter:
        cmd += " " + " ".join(shlex.quote(f) for f in test_filter)
    return cmd


def settings_path(
    root: Path,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the machine-level model-settings file path."""
    if env is None:
        env = os.environ
    if home is None:
        home = Path.home()

    # 1. Explicit override via environment variable.
    ls = env.get("LOCAL_LLM_SETTINGS", "")
    if ls:
        return Path(ls)

    # 2. Project-local dev file.
    dev_file = root / ".dev" / "local-llm.json"
    if dev_file.exists():
        return dev_file

    # 3. XDG config directory.
    xdg = env.get("XDG_CONFIG_HOME", "")
    if xdg:
        return Path(xdg) / "local-llm" / "settings.json"

    # 4. Fallback to ~/.config.
    return home / ".config" / "local-llm" / "settings.json"


# --- Internal helpers used by other server modules ---------------------------

def _default_checks(project: dict) -> list[str]:
    """Return the configured default checks for a project."""
    return list(project.get("default_checks", DEFAULTS["default_checks"]))


def _git_changed(root: Path) -> set[str]:
    """Return the set of changed files in *root* (git status --porcelain)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return set()
        files: set[str] = set()
        for line in result.stdout.splitlines():
            # Format: XY path (X=staged, Y=working tree)
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                path = parts[1].strip()
                files.add(path)
        return files
    except (OSError, subprocess.SubprocessError):
        return set()


def _settings(root: Path, env: Mapping[str, str] | None = None, home: Path | None = None) -> dict:
    """Load machine-level settings from the resolved settings path."""
    sp = settings_path(root, env, home)
    try:
        raw = sp.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        pass
    return {}


def _escalation_cmd(project: dict, check_name: str) -> str:
    """Build the escalation command for a failed check."""
    cmd = project["checks"].get(check_name) or f"npm run -s {check_name}"
    return cmd
