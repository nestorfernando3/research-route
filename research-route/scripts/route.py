from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "route-template"
FRONTMATTER_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)")


def _is_supported_value(value: object) -> bool:
    return (
        value is None
        or type(value) is int
        or isinstance(value, str)
        or isinstance(value, list)
        and all(
            item is None or type(item) is int or isinstance(item, str)
            for item in value
        )
    )


def _parse_scalar(value: str) -> object:
    if value == "null":
        return None
    if INTEGER.fullmatch(value):
        return int(value)
    if value.startswith('"') and value.endswith('"'):
        parsed = json.loads(value)
        if isinstance(parsed, str):
            return parsed
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if value.startswith("[") and value.endswith("]"):
        parsed = json.loads(value)
        if isinstance(parsed, list) and _is_supported_value(parsed):
            return parsed
    raise ValueError(f"unsupported frontmatter scalar: {value!r}")


def parse_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"missing frontmatter in {path}")

    metadata: dict[str, object] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return metadata, "".join(lines[index + 1 :])
        if line[:1].isspace():
            raise ValueError("nested YAML is not supported")
        key, separator, value = line.rstrip("\r\n").partition(":")
        if not separator or not FRONTMATTER_KEY.fullmatch(key) or not value.startswith(" "):
            raise ValueError(f"invalid flat frontmatter line: {line.rstrip()!r}")
        if key in metadata:
            raise ValueError(f"duplicate frontmatter key: {key}")
        metadata[key] = _parse_scalar(value[1:])

    raise ValueError(f"unterminated frontmatter in {path}")


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list) and _is_supported_value(value):
        return json.dumps(value, ensure_ascii=False)
    raise ValueError(f"unsupported frontmatter value: {value!r}")


def write_frontmatter(
    path: Path, metadata: dict[str, object], body: str
) -> None:
    lines = ["---\n"]
    for key, value in metadata.items():
        if not FRONTMATTER_KEY.fullmatch(key):
            raise ValueError(f"invalid frontmatter key: {key!r}")
        lines.append(f"{key}: {_format_scalar(value)}\n")
    lines.append("---\n")
    lines.append(body)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write("".join(lines))
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def init_route(destination: Path, title: str, language: str) -> Path:
    if destination.is_symlink() or destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise FileExistsError(f"destination is not empty: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
        )
    )
    try:
        shutil.copytree(TEMPLATE_ROOT, staging, dirs_exist_ok=True)
        staged_route = staging / "ROUTE.md"
        metadata, body = parse_frontmatter(staged_route)
        metadata["project_title"] = title
        metadata["language"] = language
        write_frontmatter(staged_route, metadata, body)
        staging.replace(destination)
        return destination / "ROUTE.md"
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="route.py")
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init")
    init_parser.add_argument("destination", type=Path)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--language", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "init":
            init_route(arguments.destination, arguments.title, arguments.language)
    except (FileExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
