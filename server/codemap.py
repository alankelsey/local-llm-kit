"""Compact map of a project's source files (roots from .claude/local-llm.json): one line per file with its purpose and exports."""
import re
import sys
from pathlib import Path

from project import load_project


def describe(text: str) -> str:
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == '"use client";' or stripped == "'use client';":
            continue

        # First non-blank, non-use-client line
        if stripped.startswith("//"):
            return stripped[2:].strip()

        if stripped.startswith("/*") or stripped.startswith("/**"):
            # Remove leading /* or /**
            inner = stripped[3:] if stripped.startswith("/**") else stripped[2:]
            inner = inner.strip()
            if inner.endswith("*/"):
                inner = inner[:-2].strip()

            # If still empty, look at next non-empty line
            if not inner:
                j = lines.index(line) + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line:
                        # Strip leading * and trailing */
                        next_line = next_line.replace("*/", "").strip()
                        return next_line.lstrip("*").strip()
                    j += 1

            return inner.strip()

        return ""

    return ""


def exports(text: str) -> list[str]:
    pattern = re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?(?:function|const|let|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)", re.M)
    matches = pattern.findall(text)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for name in matches:
        if name not in seen:
            seen.add(name)
            result.append(name)

    return result


def source_files(
    root: Path,
    roots: list[str] | None = None,
    extensions: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[Path]:
    if roots is None:
        roots = ["src"]
    if extensions is None:
        extensions = [".ts", ".tsx"]
    if exclude is None:
        exclude = [".test.", ".d.ts"]

    seen: set[Path] = set()
    for entry in roots:
        for matched in root.glob(entry):
            if not matched.is_dir():
                continue
            for f in matched.rglob("*"):
                if not f.is_file():
                    continue
                name = f.name
                if any(name.endswith(ext) for ext in extensions):
                    if not any(exc in name for exc in exclude):
                        seen.add(f)

    return sorted(seen, key=lambda p: p.relative_to(root).as_posix())


def build_codemap(root: Path, project: dict | None = None) -> str:
    project = project or load_project(root)
    cm = project["codemap"]
    files = source_files(root, roots=cm["roots"], extensions=cm["extensions"], exclude=cm["exclude"])
    if not files:
        return ""

    lines: list[str] = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        text = p.read_text()
        desc = describe(text) or "(no description)"
        names = exports(text)

        if names:
            line = f"{rel} — {desc} · {', '.join(names)}"
        else:
            line = f"{rel} — {desc}"
        lines.append(line)

    return "\n".join(lines) + "\n"


def missing_descriptions(root: Path, project: dict | None = None) -> list[str]:
    project = project or load_project(root)
    cm = project["codemap"]
    files = source_files(root, roots=cm["roots"], extensions=cm["extensions"], exclude=cm["exclude"])
    missing: list[str] = []

    for p in files:
        text = p.read_text()
        if describe(text) == "":
            rel = p.relative_to(root).as_posix()
            missing.append(rel)

    missing.sort()
    return missing


def main(argv: list[str], root: Path | None = None) -> int:
    # Parse --root from argv (takes precedence over the root argument)
    if "--root" in argv:
        idx = argv.index("--root")
        if idx + 1 < len(argv):
            root = Path(argv[idx + 1])

    if root is None:
        root = Path.cwd()

    project = load_project(root)

    if "--check" in argv:
        missing = missing_descriptions(root, project)
        if missing:
            print("files without a one-line header comment:")
            for p in missing:
                print(f"  {p}")
            return 1
        else:
            cm = project["codemap"]
            files = source_files(root, roots=cm["roots"], extensions=cm["extensions"], exclude=cm["exclude"])
            print(f"codemap ok ({len(files)} files)")
            return 0
    else:
        print(build_codemap(root, project), end="")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
