from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Iterator


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "route-template"
FRONTMATTER_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)")
ITEM_ID = re.compile(r"rr-[0-9]{3,}")
ALLOWED_ITEM_TYPES = {
    "question",
    "source",
    "synthesis",
    "decision",
    "writing",
    "audit",
    "human-checkpoint",
}
ALLOWED_MODES = {"light", "deep"}


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


def _frontmatter_text(metadata: dict[str, object], body: str = "") -> str:
    lines = ["---\n"]
    for key, value in metadata.items():
        if not FRONTMATTER_KEY.fullmatch(key):
            raise ValueError(f"invalid frontmatter key: {key!r}")
        lines.append(f"{key}: {_format_scalar(value)}\n")
    lines.extend(("---\n", body))
    return "".join(lines)


def write_frontmatter(
    path: Path, metadata: dict[str, object], body: str
) -> None:
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
            temporary_file.write(_frontmatter_text(metadata, body))
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _require_route(root: Path) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"invalid research route root: {root}")
    route = root / "ROUTE.md"
    if route.is_symlink() or not route.is_file():
        raise ValueError(f"missing ROUTE.md in {root}")
    return route


def _slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    if not slug:
        raise ValueError("title must contain a letter or number")
    return slug


def _validate_item_id(item_id: str) -> None:
    if not ITEM_ID.fullmatch(item_id):
        raise ValueError(f"invalid work-item ID: {item_id}")


def _require_item(root: Path, item_id: str) -> None:
    _validate_item_id(item_id)
    work_items = _require_directory(root / "work-items")
    matches = list(work_items.glob(f"{item_id}-*.md"))
    if len(matches) != 1:
        raise ValueError(f"work item not found: {item_id}")


def _require_directory(path: Path, create: bool = False) -> Path:
    if path.is_symlink():
        raise ValueError(f"symlinked directory is not allowed: {path}")
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"expected directory: {path}")
    elif create:
        path.mkdir()
    else:
        raise ValueError(f"missing directory: {path}")
    return path


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    if path.is_symlink():
        raise ValueError(f"symlinked lock is not allowed: {path}")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _write_exclusive(path: Path, content: str, mode: int) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(content)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _reserve_item_id(
    route: Path, work_items: Path, state_directory: Path
) -> str:
    allocations = _require_directory(
        state_directory / "allocations", create=True
    )
    with _exclusive_file_lock(state_directory / "allocation.lock"):
        route_metadata, route_body = parse_frontmatter(route)
        counter = route_metadata.get("next_work_item")
        if type(counter) is not int or counter < 1:
            raise ValueError("ROUTE.md next_work_item must be a positive integer")

        candidate = counter
        while True:
            item_id = f"rr-{candidate:03d}"
            reservation = allocations / f"{item_id}.reserve"
            existing_items = list(work_items.glob(f"{item_id}-*.md"))
            if not reservation.exists() and not existing_items:
                break
            candidate += 1

        _write_exclusive(
            reservation,
            json.dumps({"item_id": item_id}) + "\n",
            0o600,
        )
        route_metadata["next_work_item"] = candidate + 1
        write_frontmatter(route, route_metadata, route_body)
        return item_id


@contextmanager
def _claim_guard(state_directory: Path, item_id: str) -> Iterator[None]:
    with _exclusive_file_lock(state_directory / f"{item_id}.claim.guard"):
        yield


def new_work_item(
    root: Path,
    title: str,
    item_type: str,
    mode: str,
    dependencies: list[str],
) -> Path:
    route = _require_route(root)
    work_items = _require_directory(root / "work-items")
    if item_type not in ALLOWED_ITEM_TYPES:
        raise ValueError(f"unsupported work-item type: {item_type}")
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported work-item mode: {mode}")
    for dependency in dependencies:
        _validate_item_id(dependency)
    slug = _slugify(title)

    state_directory = _require_directory(root / ".research-route", create=True)
    item_id = _reserve_item_id(route, work_items, state_directory)
    item_path = work_items / f"{item_id}-{slug}.md"
    item_metadata: dict[str, object] = {
        "id": item_id,
        "title": title,
        "schema_version": 1,
        "type": item_type,
        "status": "open",
        "depends_on": dependencies,
        "owner": None,
        "mode": mode,
        "output": None,
    }
    _write_exclusive(item_path, _frontmatter_text(item_metadata), 0o644)
    return item_path


def claim_item(root: Path, item_id: str, owner: str) -> Path:
    _require_route(root)
    _require_item(root, item_id)
    if not owner:
        raise ValueError("owner must not be empty")
    state_directory = _require_directory(root / ".research-route", create=True)
    claims = _require_directory(state_directory / "claims", create=True)
    lock = claims / f"{item_id}.lock"
    with _claim_guard(state_directory, item_id):
        claim = {
            "item_id": item_id,
            "owner": owner,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _write_exclusive(lock, json.dumps(claim) + "\n", 0o600)
    return lock


def release_item(
    root: Path, item_id: str, owner: str, force: bool = False
) -> None:
    _require_route(root)
    _validate_item_id(item_id)
    if not owner:
        raise ValueError("owner must not be empty")
    state_directory = _require_directory(root / ".research-route")
    claims = _require_directory(state_directory / "claims")
    lock = claims / f"{item_id}.lock"
    with _claim_guard(state_directory, item_id):
        try:
            claim = json.loads(lock.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(f"work item is not claimed: {item_id}") from None
        if not isinstance(claim, dict) or claim.get("owner") != owner and not force:
            claimed_by = claim.get("owner") if isinstance(claim, dict) else "unknown"
            raise ValueError(f"claim belongs to {claimed_by}, not {owner}")
        lock.unlink()


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
    new_parser = commands.add_parser("new")
    new_parser.add_argument("--root", type=Path, required=True)
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument(
        "--type",
        dest="item_type",
        choices=sorted(ALLOWED_ITEM_TYPES),
        required=True,
    )
    new_parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), required=True)
    new_parser.add_argument("--depends-on", action="append", default=[])
    claim_parser = commands.add_parser("claim")
    claim_parser.add_argument("item_id")
    claim_parser.add_argument("--root", type=Path, required=True)
    claim_parser.add_argument("--owner", required=True)
    release_parser = commands.add_parser("release")
    release_parser.add_argument("item_id")
    release_parser.add_argument("--root", type=Path, required=True)
    release_parser.add_argument("--owner", required=True)
    release_parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "init":
            init_route(arguments.destination, arguments.title, arguments.language)
        elif arguments.command == "new":
            new_work_item(
                arguments.root,
                arguments.title,
                arguments.item_type,
                arguments.mode,
                arguments.depends_on,
            )
        elif arguments.command == "claim":
            claim_item(arguments.root, arguments.item_id, arguments.owner)
        elif arguments.command == "release":
            release_item(
                arguments.root, arguments.item_id, arguments.owner, arguments.force
            )
            if arguments.force:
                print(
                    f"warning: forcibly released claim for {arguments.item_id}",
                    file=sys.stderr,
                )
    except (FileExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
