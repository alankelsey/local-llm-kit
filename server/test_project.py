"""Contract tests for project.py: per-project config and the machine settings path."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import project  # noqa: E402


def _write_config(root: Path, data: object) -> None:
    p = root / ".claude" / "local-llm.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data))


# --- load_project ------------------------------------------------------------

def test_defaults_match_the_original_ai_wars_behaviour():
    d = project.DEFAULTS
    assert d["language"] == "TypeScript"
    assert d["conventions"] == "AGENTS.md"
    assert d["conventions_for"] == [".ts", ".tsx"]
    assert d["conventions_skip"] == ["Workflow"]
    assert d["codemap"] == {"roots": ["src"], "extensions": [".ts", ".tsx"], "exclude": [".test.", ".d.ts"]}
    assert d["aliases"] == {"@/": "src/"}
    assert d["checks"] == {
        "lint": "npm run -s lint",
        "typecheck": "npm run -s typecheck",
        "test": "npm run -s test --",
    }
    assert d["default_checks"] == ["lint", "typecheck", "test"]
    assert d["test_check"] == "test"


def test_missing_file_gives_a_copy_of_defaults(tmp_path):
    got = project.load_project(tmp_path)
    assert got == project.DEFAULTS
    got["codemap"]["roots"].append("lib")
    got["checks"]["x"] = "y"
    assert project.DEFAULTS["codemap"]["roots"] == ["src"]  # deep copy: callers can't mutate DEFAULTS
    assert "x" not in project.DEFAULTS["checks"]


def test_bad_json_or_non_object_gives_defaults(tmp_path):
    _write_config(tmp_path, "{not json")
    assert project.load_project(tmp_path) == project.DEFAULTS
    _write_config(tmp_path, [1, 2])
    assert project.load_project(tmp_path) == project.DEFAULTS


def test_top_level_keys_replace_and_codemap_merges_key_by_key(tmp_path):
    _write_config(tmp_path, {
        "language": "TypeScript (Vite monorepo)",
        "checks": {"test": "npx vitest run"},
        "default_checks": ["test"],
        "codemap": {"roots": ["packages/*/src"]},
        "extra": 1,
    })
    got = project.load_project(tmp_path)
    assert got["language"] == "TypeScript (Vite monorepo)"
    assert got["checks"] == {"test": "npx vitest run"}  # replaced, not merged
    assert got["default_checks"] == ["test"]
    assert got["codemap"] == {"roots": ["packages/*/src"], "extensions": [".ts", ".tsx"], "exclude": [".test.", ".d.ts"]}
    assert got["extra"] == 1
    assert got["aliases"] == {"@/": "src/"}


def test_values_of_the_wrong_type_keep_the_default(tmp_path):
    _write_config(tmp_path, {"language": 5, "checks": ["lint"], "codemap": {"roots": "src", "extensions": [".py"]}})
    got = project.load_project(tmp_path)
    assert got["language"] == "TypeScript"
    assert got["checks"] == project.DEFAULTS["checks"]
    assert got["codemap"]["roots"] == ["src"]
    assert got["codemap"]["extensions"] == [".py"]


def test_empty_conventions_string_is_allowed(tmp_path):
    _write_config(tmp_path, {"conventions": ""})
    assert project.load_project(tmp_path)["conventions"] == ""


# --- check_command -----------------------------------------------------------

def test_check_command_appends_quoted_filters_only_to_the_test_check():
    p = project.load_project(Path("/nonexistent"))
    assert project.check_command(p, "lint", ["src/a.test.ts"]) == "npm run -s lint"
    assert project.check_command(p, "test", []) == "npm run -s test --"
    assert project.check_command(p, "test", ["src/a b.test.ts", "src/c.test.ts"]) == (
        "npm run -s test -- 'src/a b.test.ts' src/c.test.ts"
    )


def test_check_command_unknown_name_falls_back_to_npm_script():
    p = project.load_project(Path("/nonexistent"))
    assert project.check_command(p, "build", []) == "npm run -s build"


def test_check_command_uses_configured_test_check(tmp_path):
    _write_config(tmp_path, {"checks": {"unit": "uv run pytest -q"}, "test_check": "unit"})
    p = project.load_project(tmp_path)
    assert project.check_command(p, "unit", ["server/test_x.py"]) == "uv run pytest -q server/test_x.py"


# --- settings_path -----------------------------------------------------------

def test_settings_path_env_wins(tmp_path):
    env = {"LOCAL_LLM_SETTINGS": str(tmp_path / "s.json")}
    assert project.settings_path(tmp_path, env, tmp_path / "home") == tmp_path / "s.json"


def test_settings_path_project_dev_file_when_present(tmp_path):
    dev = tmp_path / ".dev" / "local-llm.json"
    dev.parent.mkdir()
    dev.write_text("{}")
    assert project.settings_path(tmp_path, {}, tmp_path / "home") == dev


def test_settings_path_user_config_otherwise(tmp_path):
    home = tmp_path / "home"
    assert project.settings_path(tmp_path, {}, home) == home / ".config" / "local-llm" / "settings.json"
    xdg = {"XDG_CONFIG_HOME": str(tmp_path / "xdg")}
    assert project.settings_path(tmp_path, xdg, home) == tmp_path / "xdg" / "local-llm" / "settings.json"
