from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from typing import Callable, Iterator


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "route-template"
FRONTMATTER_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)")
ITEM_ID = re.compile(r"rr-[0-9]{3,}")
SOURCE_ID = re.compile(r"(?<![A-Za-z0-9])S-[0-9]{2}[a-z]?(?![A-Za-z0-9])", re.IGNORECASE)
ALLOWED_ITEM_TYPES = {
    "question",
    "source",
    "synthesis",
    "decision",
    "writing",
    "audit",
    "human-checkpoint",
    "venue",
    "ethics",
    "review",
    "submission",
}
ALLOWED_MODES = {"light", "deep"}
ALLOWED_STATUSES = {"open", "closed", "provisional", "verified", "cancelled"}
ALLOWED_CYCLES = {"discover", "argue", "compose", "audit"}
ALLOWED_SCHEMA_VERSIONS = {1, 2}
PROJECT_SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
ALLOWED_RISKS = {"routine", "material", "critical"}
ALLOWED_REVIEW_STATUSES = {"none", "deferred", "reviewed"}
RISK_ORDER = {"routine": 0, "material": 1, "critical": 2}
ALLOWED_CLAIM_STATES = {
    "supported",
    "inferred",
    "provisional",
    "disputed",
    "unverified",
}
ALLOWED_SOURCE_USE = {"candidate", "used", "decisive", "adverse"}
REQUIRED_FILES = (
    "ROUTE.md",
    "INQUIRY.md",
    "VENUE.md",
    "CLAIMS.md",
    "DECISIONS.md",
    "RESEARCHER.md",
    "HANDOFF.md",
    "manuscript/OUTLINE.md",
    "manuscript/VOICE.md",
    "references/library.bib",
)
REQUIRED_DIRECTORIES = (
    "work-items",
    "sources",
    "manuscript",
    "manuscript/sections",
    "references",
)
ROUTE_FIELDS = {
    "schema_version",
    "project_title",
    "language",
    "current_cycle",
    "target_venue",
    "fallback_venue",
    "next_work_item",
}
ITEM_FIELDS = {
    "id",
    "title",
    "schema_version",
    "type",
    "status",
    "depends_on",
    "owner",
    "mode",
    "output",
}
V2_ITEM_FIELDS = ITEM_FIELDS | {
    "risk",
    "review_status",
    "acceptance",
    "verification",
    "result",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"!?\[([^\]]+)\]\[([^\]]*)\]")
SHORTCUT_REFERENCE = re.compile(r"(?<!!)\[([^\]\n]+)\](?![\[(]|:)")
REFERENCE_DEFINITION = re.compile(
    r"(?m)^[ \t]{0,3}\[([^\]]+)\]:[ \t]*(?:<([^>\n]+)>|(\S+))"
)
HANDOFF_BEGIN = b"<!-- BEGIN ROUTE MECHANICAL -->"
HANDOFF_END = b"<!-- END ROUTE MECHANICAL -->"
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)


class _PublishedStaleHandoff(Exception):
    pass


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


def _risk_for_item(item_type: str, mode: str = "light") -> str:
    """Assign a conservative default risk while allowing cheap exploration."""
    if item_type in {"ethics", "submission", "human-checkpoint"}:
        return "critical"
    if item_type in {"source", "venue", "review"}:
        return "material" if mode == "light" else "critical"
    if item_type in {"decision", "synthesis"}:
        return "material" if mode == "light" else "critical"
    return "routine"


def _requested_risk(item_type: str, mode: str, requested: str | None) -> str:
    default = _risk_for_item(item_type, mode)
    if requested is None:
        return default
    if requested not in ALLOWED_RISKS:
        raise ValueError(f"unsupported risk: {requested}")
    if RISK_ORDER[requested] < RISK_ORDER[default]:
        raise ValueError(f"cannot lower automatic risk {default} to {requested}")
    return requested


def _schema_version(metadata: dict[str, object]) -> int:
    value = metadata.get("schema_version")
    return value if type(value) is int else LEGACY_SCHEMA_VERSION


def _is_v2_root(metadata: dict[str, object]) -> bool:
    return _schema_version(metadata) >= PROJECT_SCHEMA_VERSION


def _atomic_write_bytes_at(
    directory_fd: int,
    name: str,
    content: bytes,
    pre_replace: Callable[[], bool] | None = None,
) -> None:
    try:
        mode = stat.S_IMODE(os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode)
    except OSError:
        raise ValueError(f"unsafe file: {name}") from None
    temporary_name = f".{name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary_name, flags, mode, dir_fd=directory_fd)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
        if pre_replace is not None and not pre_replace():
            raise ValueError("ROUTE.md changed while generating handoff")
        os.replace(
            temporary_name,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


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


def _parse_frontmatter_text(
    text: str, source: Path
) -> tuple[dict[str, object], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"missing frontmatter in {source}")

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

    raise ValueError(f"unterminated frontmatter in {source}")


def parse_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    return _parse_frontmatter_text(path.read_text(encoding="utf-8"), path)


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


def _stat_signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_route_snapshot(
    root_fd: int,
) -> tuple[dict[str, object], str, tuple[int, int, int, int, int]]:
    for _ in range(3):
        before = os.stat("ROUTE.md", dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("invalid ROUTE.md")
        descriptor = os.open(
            "ROUTE.md",
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            content = stream.read()
            after_read = os.fstat(stream.fileno())
        after = os.stat("ROUTE.md", dir_fd=root_fd, follow_symlinks=False)
        signature = _stat_signature(opened)
        if (
            signature == _stat_signature(before)
            and signature == _stat_signature(after_read)
            and signature == _stat_signature(after)
        ):
            text = content.decode("utf-8")
            metadata, body = _parse_frontmatter_text(text, Path("ROUTE.md"))
            return metadata, body, signature
    raise ValueError("ROUTE.md changed while reading handoff state")


def _route_snapshot_is_current(
    root_fd: int, signature: tuple[int, int, int, int, int]
) -> bool:
    try:
        current = os.stat("ROUTE.md", dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISREG(current.st_mode) and _stat_signature(current) == signature


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


@contextmanager
def _directory_at(
    parent_fd: int,
    name: str,
    create: bool = False,
    missing_ok: bool = False,
) -> Iterator[int | None]:
    if create:
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
    try:
        descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if missing_ok:
            yield None
            return
        raise
    except OSError:
        raise ValueError(f"unsafe directory: {name}") from None
    try:
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _state_directory_fd(
    root: Path, create: bool = False, missing_ok: bool = False
) -> Iterator[tuple[int, int | None]]:
    try:
        root_fd = os.open(root, DIRECTORY_FLAGS)
    except OSError:
        raise ValueError(f"invalid research route root: {root}") from None
    try:
        with _directory_at(
            root_fd, ".research-route", create, missing_ok
        ) as state_fd:
            yield root_fd, state_fd
    finally:
        os.close(root_fd)


@contextmanager
def _exclusive_file_lock_at(directory_fd: int, name: str) -> Iterator[None]:
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    while True:
        try:
            descriptor = os.open(name, flags, dir_fd=directory_fd)
            break
        except FileNotFoundError:
            try:
                descriptor = os.open(
                    name,
                    flags | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=directory_fd,
                )
                break
            except FileExistsError:
                continue
        except OSError:
            raise ValueError(f"unsafe lock: {name}") from None
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError(f"unsafe lock: {name}")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _write_exclusive_at(
    directory_fd: int, name: str, content: str, mode: int
) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, mode, dir_fd=directory_fd)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(content)
    except Exception:
        os.unlink(name, dir_fd=directory_fd)
        raise


def _read_regular_text_at(directory_fd: int, name: str) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError:
        raise ValueError(f"unsafe file: {name}") from None
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f"unsafe file: {name}")
        return stream.read()


def _parse_frontmatter_at(
    directory_fd: int, name: str, source: Path | None = None
) -> tuple[dict[str, object], str]:
    text = _read_regular_text_at(directory_fd, name)
    return _parse_frontmatter_text(
        text, source or Path(name)
    )


def _require_file_at(root_fd: int, root: Path, name: str) -> None:
    if not stat.S_ISREG(_relative_kind_at(root_fd, name) or 0):
        raise ValueError(f"missing {name} in {root}")


def _write_frontmatter_at(
    directory_fd: int, name: str, metadata: dict[str, object], body: str
) -> None:
    _atomic_write_bytes_at(
        directory_fd, name, _frontmatter_text(metadata, body).encode("utf-8")
    )


def _exists_at(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


@contextmanager
def _relative_parent_fd(root_fd: int, relative_path: str) -> Iterator[tuple[int, str]]:
    parts = Path(relative_path).parts
    descriptor = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(part, DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def _relative_kind_at(root_fd: int, relative_path: str) -> int | None:
    try:
        with _relative_parent_fd(root_fd, relative_path) as (parent_fd, name):
            return os.stat(name, dir_fd=parent_fd, follow_symlinks=False).st_mode
    except OSError:
        return None


def _markdown_files_at(
    directory_fd: int, prefix: str = "", skip_root: frozenset[str] = frozenset()
) -> Iterator[tuple[str, str]]:
    for name in sorted(os.listdir(directory_fd)):
        if not prefix and (name == ".research-route" or name in skip_root):
            continue
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        relative_path = f"{prefix}/{name}" if prefix else name
        if stat.S_ISDIR(info.st_mode):
            with _directory_at(directory_fd, name) as child_fd:
                assert child_fd is not None
                yield from _markdown_files_at(child_fd, relative_path)
        elif stat.S_ISREG(info.st_mode) and name.endswith(".md"):
            yield relative_path, _read_regular_text_at(directory_fd, name)


def _item_name_at(work_items_fd: int, item_id: str) -> str:
    _validate_item_id(item_id)
    matches = [
        name
        for name in os.listdir(work_items_fd)
        if name.startswith(f"{item_id}-") and name.endswith(".md")
    ]
    if len(matches) != 1:
        raise ValueError(f"work item not found: {item_id}")
    info = os.stat(matches[0], dir_fd=work_items_fd, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"invalid work item: {item_id}")
    return matches[0]


def _reserve_item_id(root_fd: int, work_items_fd: int, state_fd: int) -> str:
    with _directory_at(state_fd, "allocations", create=True) as allocations_fd:
        with _exclusive_file_lock_at(state_fd, "allocation.lock"):
            route_metadata, route_body = _parse_frontmatter_at(root_fd, "ROUTE.md")
            counter = route_metadata.get("next_work_item")
            if type(counter) is not int or counter < 1:
                raise ValueError("ROUTE.md next_work_item must be a positive integer")

            candidate = counter
            while True:
                item_id = f"rr-{candidate:03d}"
                reservation = f"{item_id}.reserve"
                existing_items = [
                    name
                    for name in os.listdir(work_items_fd)
                    if name.startswith(f"{item_id}-") and name.endswith(".md")
                ]
                if not _exists_at(allocations_fd, reservation) and not existing_items:
                    break
                candidate += 1

            _write_exclusive_at(
                allocations_fd,
                reservation,
                json.dumps({"item_id": item_id}) + "\n",
                0o600,
            )
            route_metadata["next_work_item"] = candidate + 1
            _write_frontmatter_at(root_fd, "ROUTE.md", route_metadata, route_body)
            return item_id


@contextmanager
def _claim_guard(state_fd: int) -> Iterator[None]:
    with _exclusive_file_lock_at(state_fd, "claims.guard"):
        yield


def new_work_item(
    root: Path,
    title: str,
    item_type: str,
    mode: str,
    dependencies: list[str],
    risk: str | None = None,
) -> Path:
    if item_type not in ALLOWED_ITEM_TYPES:
        raise ValueError(f"unsupported work-item type: {item_type}")
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported work-item mode: {mode}")
    for dependency in dependencies:
        _validate_item_id(dependency)
    slug = _slugify(title)

    item_name = ""
    with _state_directory_fd(root, create=True) as (root_fd, state_fd):
        assert state_fd is not None
        with _claim_guard(state_fd):
            _require_file_at(root_fd, root, "ROUTE.md")
            route_metadata, _ = _parse_frontmatter_at(root_fd, "ROUTE.md")
            project_v2 = _is_v2_root(route_metadata)
            with _directory_at(root_fd, "work-items") as work_items_fd:
                assert work_items_fd is not None
                item_id = _reserve_item_id(root_fd, work_items_fd, state_fd)
                item_name = f"{item_id}-{slug}.md"
                item_metadata: dict[str, object] = {
                    "id": item_id,
                    "title": title,
                    "schema_version": 2 if project_v2 else 1,
                    "type": item_type,
                    "status": "open",
                    "depends_on": dependencies,
                    "owner": None,
                    "mode": mode,
                    "output": None,
                }
                if project_v2:
                    item_metadata.update(
                        {
                            "risk": _requested_risk(item_type, mode, risk),
                            "review_status": "none",
                            "acceptance": ["Record a defensible result and link its canonical output."],
                            "verification": [],
                            "result": None,
                        }
                    )
                body = (
                    f"\n# {title}\n\n"
                    f"## Question or deliverable\n\n{title}\n\n"
                    "## Closure criteria\n\n"
                    "Record a defensible result and link its canonical output.\n"
                )
                _write_exclusive_at(
                    work_items_fd,
                    item_name,
                    _frontmatter_text(item_metadata, body),
                    0o644,
                )
    return root / "work-items" / item_name


def claim_item(root: Path, item_id: str, owner: str) -> Path:
    _validate_item_id(item_id)
    if not owner:
        raise ValueError("owner must not be empty")
    lock = root / ".research-route" / "claims" / f"{item_id}.lock"
    with _state_directory_fd(root, create=True) as (root_fd, state_fd):
        assert state_fd is not None
        with _claim_guard(state_fd):
            with _directory_at(state_fd, "claims", create=True) as claims_fd:
                _require_file_at(root_fd, root, "ROUTE.md")
                _parse_frontmatter_at(root_fd, "ROUTE.md")
                with _directory_at(root_fd, "work-items") as work_items_fd:
                    assert work_items_fd is not None
                    item_name = _item_name_at(work_items_fd, item_id)
                    item_path = root / "work-items" / item_name
                    item, _ = _parse_frontmatter_at(
                        work_items_fd, item_name, item_path
                    )
                    record_errors = _work_item_record_errors(item)
                    if record_errors:
                        raise ValueError(
                            f"invalid work item {item_path}: {record_errors[0][1]}"
                        )
                    if item.get("status") not in {"open", "provisional"}:
                        raise ValueError(f"work item is not open: {item_id}")
                    dependencies = item.get("depends_on")
                    assert isinstance(dependencies, list)
                    unclosed: list[str] = []
                    for dependency in dependencies:
                        assert isinstance(dependency, str)
                        dependency_name = _item_name_at(work_items_fd, dependency)
                        dependency_path = root / "work-items" / dependency_name
                        dependency_item, _ = _parse_frontmatter_at(
                            work_items_fd, dependency_name, dependency_path
                        )
                        dependency_errors = _work_item_record_errors(dependency_item)
                        if dependency_errors:
                            raise ValueError(
                                f"invalid work item {dependency_path}: "
                                f"{dependency_errors[0][1]}"
                            )
                        if dependency_item.get("status") not in {"closed", "verified"}:
                            unclosed.append(dependency)
                if unclosed:
                    raise ValueError(
                        "work item dependencies are not closed: "
                        + ", ".join(unclosed)
                    )
                claim = {
                    "item_id": item_id,
                    "owner": owner,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                _write_exclusive_at(
                    claims_fd, f"{item_id}.lock", json.dumps(claim) + "\n", 0o600
                )
    return lock


def release_item(
    root: Path, item_id: str, owner: str, force: bool = False
) -> None:
    _validate_item_id(item_id)
    if not owner:
        raise ValueError("owner must not be empty")
    lock = root / ".research-route" / "claims" / f"{item_id}.lock"
    with _state_directory_fd(root) as (root_fd, state_fd):
        assert state_fd is not None
        with _claim_guard(state_fd):
            _require_file_at(root_fd, root, "ROUTE.md")
            _parse_frontmatter_at(root_fd, "ROUTE.md")
            with _directory_at(state_fd, "claims") as claims_fd:
                try:
                    claim = json.loads(
                        _read_regular_text_at(claims_fd, f"{item_id}.lock")
                    )
                except ValueError as error:
                    if not _exists_at(claims_fd, f"{item_id}.lock"):
                        raise ValueError(
                            f"work item is not claimed: {item_id}"
                        ) from None
                    raise error
                claim_errors = _claim_record_errors(claim)
                if claim_errors:
                    raise ValueError(f"invalid claim {lock}: {claim_errors[0]}")
                if (
                    not isinstance(claim, dict)
                    or claim.get("owner") != owner
                    and not force
                ):
                    claimed_by = (
                        claim.get("owner") if isinstance(claim, dict) else "unknown"
                    )
                    raise ValueError(f"claim belongs to {claimed_by}, not {owner}")
                os.unlink(f"{item_id}.lock", dir_fd=claims_fd)


def _normalize_output_path(output: str) -> str:
    if not isinstance(output, str) or not output.strip() or "\x00" in output:
        raise ValueError("output must be a non-empty project-relative path")
    candidate = output.strip().replace("\\", "/")
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        raise ValueError("output must be a non-empty project-relative path")
    if ".." in candidate.split("/"):
        raise ValueError("output must be a normalized project-relative path")
    normalized = posixpath.normpath(candidate)
    if normalized in {"", "."} or normalized.startswith("../"):
        raise ValueError("output must be a normalized project-relative path")
    return normalized


def _output_is_regular_file(root_fd: int, output: str) -> bool:
    try:
        with _relative_parent_fd(root_fd, output) as (parent_fd, name):
            info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                return False
            descriptor = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            try:
                return stat.S_ISREG(os.fstat(descriptor).st_mode)
            finally:
                os.close(descriptor)
    except (OSError, ValueError):
        return False


def complete_item(
    root: Path,
    item_id: str,
    owner: str,
    output: str,
    verification: list[str] | None = None,
    result: str | None = None,
    provisional: bool = False,
) -> Path:
    _validate_item_id(item_id)
    if not owner:
        raise ValueError("owner must not be empty")
    normalized_output = _normalize_output_path(output)
    with _state_directory_fd(root) as (root_fd, state_fd):
        assert state_fd is not None
        with _claim_guard(state_fd):
            _require_file_at(root_fd, root, "ROUTE.md")
            _parse_frontmatter_at(root_fd, "ROUTE.md")
            with _directory_at(root_fd, "work-items") as work_items_fd:
                assert work_items_fd is not None
                item_name = _item_name_at(work_items_fd, item_id)
                item_path = root / "work-items" / item_name
                item, body = _parse_frontmatter_at(
                    work_items_fd, item_name, item_path
                )
                record_errors = _work_item_record_errors(item)
                if record_errors:
                    raise ValueError(
                        f"invalid work item {item_path}: {record_errors[0][1]}"
                    )
                if not _output_is_regular_file(root_fd, normalized_output):
                    raise ValueError(
                        "output must resolve to an existing regular file inside the project root"
                    )
                with _directory_at(state_fd, "claims") as claims_fd:
                    claim_name = f"{item_id}.lock"
                    if not _exists_at(claims_fd, claim_name):
                        raise ValueError(f"work item is not claimed: {item_id}")
                    try:
                        claim = json.loads(
                            _read_regular_text_at(claims_fd, claim_name)
                        )
                    except (ValueError, json.JSONDecodeError) as error:
                        raise ValueError(f"invalid claim {root / '.research-route' / 'claims' / claim_name}: {error}") from None
                    claim_errors = _claim_record_errors(claim)
                    if claim_errors:
                        raise ValueError(
                            f"invalid claim {root / '.research-route' / 'claims' / claim_name}: {claim_errors[0]}"
                        )
                    assert isinstance(claim, dict)
                    identity_errors = _claim_identity_errors(claim, item_id)
                    if identity_errors:
                        raise ValueError(
                            f"invalid claim {root / '.research-route' / 'claims' / claim_name}: {identity_errors[0][1]}"
                        )
                    if claim.get("owner") != owner:
                        raise ValueError(
                            f"claim belongs to {claim.get('owner')}, not {owner}"
                        )
                    if item.get("status") == "closed":
                        if item.get("owner") != owner or item.get("output") != normalized_output:
                            raise ValueError(
                                "closed work item does not match the completing owner and output"
                            )
                        os.unlink(claim_name, dir_fd=claims_fd)
                        return item_path
                    if item.get("status") not in {"open", "provisional"}:
                        raise ValueError(f"unsupported work-item status: {item.get('status')}")
                    if item.get("schema_version") == 2 and not provisional:
                        if not verification or not result or not result.strip():
                            raise ValueError("v2 completion requires verification and result, or --provisional")
                        item["verification"] = verification
                        item["result"] = result
                        item["review_status"] = "reviewed"
                    if item.get("schema_version") == 2 and provisional:
                        if item.get("risk") == "critical":
                            raise ValueError("critical work cannot be deferred")
                        item["review_status"] = "deferred"
                    item["status"] = "provisional" if provisional else "closed"
                    item["owner"] = owner
                    item["output"] = normalized_output
                    _write_frontmatter_at(work_items_fd, item_name, item, body)
                    os.unlink(claim_name, dir_fd=claims_fd)
                    return item_path


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _missing_fields(
    issues: list[ValidationIssue],
    root: Path,
    path: Path,
    metadata: dict[str, object],
    required_fields: set[str],
) -> None:
    relative_path = _relative_path(root, path)
    for field in sorted(required_fields - metadata.keys()):
        issues.append(
            ValidationIssue(
                "missing-field", relative_path, f"missing required field: {field}"
            )
        )


def _claim_record_errors(claim: object) -> tuple[str, ...]:
    if not isinstance(claim, dict):
        return ("claim must be a JSON object",)
    errors: list[str] = []
    item_id = claim.get("item_id")
    if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id):
        errors.append("claim item_id must be a work-item ID")
    owner = claim.get("owner")
    if not isinstance(owner, str) or not owner:
        errors.append("claim owner must not be empty")
    try:
        _parse_aware_timestamp(claim.get("timestamp"))
    except ValueError:
        errors.append(
            "claim timestamp must be an ISO-8601 timezone-aware timestamp"
        )
    return tuple(errors)


def _parse_aware_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("timestamp must be a non-empty string")
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ValueError("timestamp is not ISO-8601") from None


def _claim_identity_errors(
    claim: dict[str, object], filename_id: str
) -> tuple[tuple[str, str], ...]:
    claimed_id = claim.get("item_id")
    if claimed_id == filename_id:
        return ()
    return (
        (
            "claim-mismatch",
            f"claim item_id {claimed_id!r} does not match {filename_id!r}",
        ),
    )


def _claim_reference_errors(
    claim: dict[str, object], filename_id: str, known_ids: set[str]
) -> tuple[tuple[str, str], ...]:
    referenced_ids = {filename_id}
    claimed_id = claim.get("item_id")
    if isinstance(claimed_id, str):
        referenced_ids.add(claimed_id)
    return tuple(
        (
            "orphan-claim",
            f"claim references missing work item: {item_id}",
        )
        for item_id in sorted(referenced_ids - known_ids)
    )


def _work_item_record_errors(
    metadata: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    schema_version = metadata.get("schema_version")
    required_fields = V2_ITEM_FIELDS if schema_version == 2 else ITEM_FIELDS
    errors: list[tuple[str, str]] = [
        ("missing-field", f"missing required field: {field}")
        for field in sorted(required_fields - metadata.keys())
    ]
    item_id = metadata.get("id")
    if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id):
        errors.append(("invalid-field", f"invalid work-item id: {item_id!r}"))
    title = metadata.get("title")
    if "title" in metadata and (
        not isinstance(title, str) or not title.strip()
    ):
        errors.append(("invalid-field", "title must be a non-empty string"))
    for field in ("owner", "output"):
        value = metadata.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(("invalid-field", f"{field} must be a string or null"))
    if schema_version not in ALLOWED_SCHEMA_VERSIONS:
        errors.append(
            ("unsupported-schema", f"unsupported schema_version: {schema_version!r}")
        )
    for field, allowed in (
        ("type", ALLOWED_ITEM_TYPES),
        ("status", ALLOWED_STATUSES),
        ("mode", ALLOWED_MODES),
    ):
        value = metadata.get(field)
        if field in metadata and (
            not isinstance(value, str) or value not in allowed
        ):
            errors.append(("invalid-enum", f"unsupported {field}: {value!r}"))
    dependencies = metadata.get("depends_on")
    if not isinstance(dependencies, list) or not all(
        isinstance(dependency, str) and ITEM_ID.fullmatch(dependency)
        for dependency in dependencies
    ):
        errors.append(
            ("invalid-field", "depends_on must be a list of work-item IDs")
        )
    if schema_version == 2:
        risk = metadata.get("risk")
        if not isinstance(risk, str) or risk not in ALLOWED_RISKS:
            errors.append(("invalid-enum", f"unsupported risk: {risk!r}"))
        review_status = metadata.get("review_status")
        if not isinstance(review_status, str) or review_status not in ALLOWED_REVIEW_STATUSES:
            errors.append(
                ("invalid-enum", f"unsupported review_status: {review_status!r}")
            )
        for field in ("acceptance", "verification"):
            value = metadata.get(field)
            if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
                errors.append(("invalid-field", f"{field} must be a list of strings"))
        result = metadata.get("result")
        if result is not None and not isinstance(result, str):
            errors.append(("invalid-field", "result must be a string or null"))
    return tuple(errors)


def _work_item_section_errors(body: str) -> tuple[tuple[str, str], ...]:
    errors: list[tuple[str, str]] = []
    for heading in ("Question or deliverable", "Closure criteria"):
        matches = re.findall(
            rf"(?ms)^## {re.escape(heading)}[ \t]*\r?\n(.*?)(?=^## |\Z)",
            body,
        )
        if not matches:
            errors.append(
                ("invalid-section", f"missing required section: {heading}")
            )
            continue
        if len(matches) > 1:
            errors.append(
                ("invalid-section", f"duplicate required section: {heading}")
            )
            continue
        content = re.sub(r"<!--.*?-->", "", matches[0], flags=re.DOTALL)
        if not any(character.isalnum() for character in content):
            errors.append(
                (
                    "invalid-section",
                    f"{heading} must contain substantive text",
                )
            )
    return tuple(errors)


def _claim_compatibility_errors(
    claim: dict[str, object], items: dict[str, dict[str, object]]
) -> tuple[str, ...]:
    item_id = claim.get("item_id")
    if not isinstance(item_id, str) or item_id not in items:
        return ()
    item = items[item_id]
    errors: list[str] = []
    if item.get("status") != "open":
        errors.append(f"claim targets non-open work item: {item_id}")
    dependencies = item.get("depends_on")
    if isinstance(dependencies, list):
        unclosed = [
            dependency
            for dependency in dependencies
            if isinstance(dependency, str)
            and items.get(dependency, {}).get("status") != "closed"
        ]
        if unclosed:
            errors.append(
                "claim targets work with unclosed dependencies: "
                + ", ".join(unclosed)
            )
    return tuple(errors)


def _duplicate_item_issues(
    root: Path, items_by_id: dict[str, list[Path]]
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for item_id, paths in sorted(items_by_id.items()):
        if len(paths) < 2:
            continue
        names = ", ".join(_relative_path(root, path) for path in paths)
        issues.extend(
            ValidationIssue(
                "duplicate-id",
                _relative_path(root, path),
                f"work-item id {item_id} is duplicated in: {names}",
            )
            for path in paths
        )
    return tuple(issues)


def _dependency_cycles(graph: dict[str, list[str]]) -> list[tuple[str, ...]]:
    state: dict[str, int] = {}
    cycles: set[tuple[str, ...]] = set()

    for item_id in sorted(graph):
        if state.get(item_id, 0) != 0:
            continue
        state[item_id] = 1
        path = [item_id]
        positions = {item_id: 0}
        frames: list[tuple[str, Iterator[str]]] = [
            (item_id, iter(sorted(graph.get(item_id, []))))
        ]
        while frames:
            current, dependencies = frames[-1]
            try:
                dependency = next(dependencies)
            except StopIteration:
                frames.pop()
                path.pop()
                positions.pop(current)
                state[current] = 2
                continue
            if dependency not in graph:
                continue
            dependency_state = state.get(dependency, 0)
            if dependency_state == 0:
                state[dependency] = 1
                positions[dependency] = len(path)
                path.append(dependency)
                frames.append(
                    (dependency, iter(sorted(graph.get(dependency, []))))
                )
            elif dependency_state == 1:
                cycle = path[positions[dependency] :]
                smallest = min(range(len(cycle)), key=cycle.__getitem__)
                cycles.add(tuple(cycle[smallest:] + cycle[:smallest]))
    return sorted(cycles)


def _reference_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def _broken_markdown_target(
    root_fd: int,
    work_items_fd: int | None,
    relative_path: str,
    destination: str,
) -> bool:
    lowered = destination.lower()
    if (
        not destination
        or destination.startswith("#")
        or lowered.startswith(("http:", "https:", "mailto:"))
        or destination.startswith("/")
    ):
        return False
    target_text = destination.partition("#")[0].partition("?")[0]
    if not target_text:
        return False
    target = posixpath.normpath(
        posixpath.join(posixpath.dirname(relative_path), target_text)
    )
    if target == ".." or target.startswith("../"):
        return True
    if work_items_fd is not None and target == "work-items":
        return False
    if work_items_fd is not None and target.startswith("work-items/"):
        return _relative_kind_at(work_items_fd, target.removeprefix("work-items/")) is None
    return _relative_kind_at(root_fd, target) is None


def _validate_markdown_links(
    root_fd: int, issues: list[ValidationIssue], work_items_fd: int | None
) -> None:
    markdown_files = _markdown_files_at(root_fd, skip_root=frozenset({"work-items"}))
    if work_items_fd is not None:
        markdown_files = iter(
            (*markdown_files, *_markdown_files_at(work_items_fd, "work-items"))
        )
    for relative_path, text in markdown_files:
        link_text = text
        if relative_path == "RESEARCHER.md":
            link_text = re.sub(
                r"(?ms)(^## Private[ \t]*\r?\n).*?(?=^## |\Z)",
                r"\1",
                text,
            )
        for match in MARKDOWN_LINK.finditer(link_text):
            destination = match.group(1).strip()
            if destination.startswith("<") and ">" in destination:
                destination = destination[1 : destination.index(">")]
            else:
                destination = destination.split(maxsplit=1)[0]
            if _broken_markdown_target(
                root_fd, work_items_fd, relative_path, destination
            ):
                issues.append(
                    ValidationIssue(
                        "broken-link",
                        relative_path,
                        f"relative link does not exist: {destination}",
                    )
                )
        definitions: dict[str, str] = {}
        for match in REFERENCE_DEFINITION.finditer(link_text):
            label = _reference_label(match.group(1))
            definitions.setdefault(label, match.group(2) or match.group(3))
        references = {
            _reference_label(match.group(2) or match.group(1))
            for match in REFERENCE_LINK.finditer(link_text)
        }
        references.update(
            label
            for match in SHORTCUT_REFERENCE.finditer(link_text)
            if (label := _reference_label(match.group(1))) in definitions
        )
        for label in sorted(references):
            destination = definitions.get(label)
            if destination is None:
                issues.append(
                    ValidationIssue(
                        "broken-link",
                        relative_path,
                        f"reference definition does not exist: {label}",
                    )
                )
            elif _broken_markdown_target(
                root_fd, work_items_fd, relative_path, destination
            ):
                issues.append(
                    ValidationIssue(
                        "broken-link",
                        relative_path,
                        f"relative link does not exist: {destination}",
                    )
                )


def _parse_handoff_snapshot(mechanical: bytes) -> datetime:
    text = mechanical.decode("utf-8")
    for heading in (
        "Open frontier candidates",
        "Active claims",
        "Blocks",
        "Exact next action",
    ):
        if len(re.findall(rf"(?m)^### {re.escape(heading)}[ \t]*$", text)) != 1:
            raise ValueError(f"duplicate or missing mechanical heading: {heading}")
    if len(re.findall(r"(?m)^### Deferred review[ \t]*$", text)) > 1:
        raise ValueError("duplicate mechanical heading: Deferred review")
    match = re.fullmatch(
        r"\n\n"
        r"- Project: (?P<project>[^\r\n]+)\n"
        r"- Schema version: (?P<schema>[0-9]+)\n"
        r"- Current cycle: (?P<cycle>[^\r\n]+)\n"
        r"- Target venue: (?P<target>[^\r\n]+)\n"
        r"- Fallback venue: (?P<fallback>[^\r\n]+)\n"
        r"- Generated at: (?P<generated>[^\r\n]+)\n"
        r"- ROUTE\.md modified: (?P<modified>[^\r\n]+)\n\n"
        r"### Open frontier candidates\n\n(?P<frontier>.+?)\n\n"
        r"### Active claims\n\n(?P<claims>.+?)\n\n"
        r"(?:### Deferred review\n\n(?P<deferred>.+?)\n\n)?"
        r"### Blocks\n\n(?P<blocks>.+?)\n\n"
        r"### Exact next action\n\n(?P<action>.+?)\n\n",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("mechanical snapshot does not match the handoff schema")
    if match.group("cycle") not in ALLOWED_CYCLES:
        raise ValueError("invalid current cycle in mechanical snapshot")
    for section in ("frontier", "claims"):
        value = match.group(section)
        if value != "- None" and any(
            re.fullmatch(r"- rr-[0-9]{3,}: .+", line) is None
            for line in value.splitlines()
        ):
            raise ValueError(f"invalid {section} entries in mechanical snapshot")
    deferred = match.group("deferred")
    if deferred and deferred != "- None" and any(
        re.fullmatch(r"- rr-[0-9]{3,}: .+ \(risk: .+\)", line) is None
        for line in deferred.splitlines()
    ):
        raise ValueError("invalid deferred review entries in mechanical snapshot")
    now = datetime.now(timezone.utc)
    generated = _parse_aware_timestamp(match.group("generated"))
    modified = _parse_aware_timestamp(match.group("modified"))
    if generated > now + timedelta(minutes=5) or modified > now + timedelta(minutes=5):
        raise ValueError("mechanical snapshot timestamp is in the future")
    return modified


def _handoff_freshness_issue(root_fd: int) -> ValidationIssue | None:
    if not stat.S_ISREG(_relative_kind_at(root_fd, "HANDOFF.md") or 0):
        return None
    try:
        content = _read_regular_text_at(root_fd, "HANDOFF.md").encode("utf-8")
    except (UnicodeError, ValueError) as error:
        return ValidationIssue("invalid-handoff", "HANDOFF.md", str(error))
    if (
        content.count(HANDOFF_BEGIN) != 1
        or content.count(HANDOFF_END) != 1
        or content.index(HANDOFF_BEGIN) > content.index(HANDOFF_END)
    ):
        return ValidationIssue(
            "invalid-handoff",
            "HANDOFF.md",
            "mechanical snapshot markers are missing, duplicated, or out of order",
        )
    mechanical = content.split(HANDOFF_BEGIN, 1)[1].split(HANDOFF_END, 1)[0]
    if not mechanical.strip():
        return None
    try:
        snapshot = _parse_handoff_snapshot(mechanical)
    except (UnicodeError, ValueError) as error:
        return ValidationIssue("invalid-handoff", "HANDOFF.md", str(error))
    snapshot_text = snapshot.isoformat()
    fraction = re.search(r"T\d{2}:\d{2}:\d{2}[.,](\d+)", snapshot_text)
    resolution = 10 ** -min(len(fraction.group(1)), 6) if fraction else 1.0
    current = datetime.fromtimestamp(
        os.stat("ROUTE.md", dir_fd=root_fd, follow_symlinks=False).st_mtime,
        timezone.utc,
    )
    if (current - snapshot).total_seconds() < resolution:
        return None
    return ValidationIssue(
        "stale-handoff",
        "HANDOFF.md",
        "mechanical snapshot predates the current ROUTE.md",
    )


def _section_content(body: str, heading: str) -> tuple[str | None, bool]:
    matches = re.findall(
        rf"(?ms)^## {re.escape(heading)}[ \t]*\r?\n(.*?)(?=^## |\Z)",
        body,
    )
    return (matches[0].strip(), len(matches) == 1) if len(matches) == 1 else (None, bool(matches))


def _has_declared_text(content: str | None) -> bool:
    if content is None:
        return False
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
    return any(character.isalnum() for character in content)


def _privacy_issue(root_fd: int) -> ValidationIssue | None:
    if not stat.S_ISREG(_relative_kind_at(root_fd, "RESEARCHER.md") or 0):
        return None
    try:
        body = _read_regular_text_at(root_fd, "RESEARCHER.md")
    except (OSError, UnicodeError, ValueError):
        return None
    private, present = _section_content(body, "Private")
    private_text = re.sub(r"<!--.*?-->", "", private or "", flags=re.DOTALL).strip()
    if present and _has_declared_text(private) and private_text.casefold() not in {"none", "- none"}:
        return ValidationIssue(
            "privacy-boundary",
            "RESEARCHER.md",
            "legacy Private content must be relocated or deleted outside the portable project root",
        )
    return None


def _handoff_checkpoint_issues(root_fd: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    try:
        _, route_body = _parse_frontmatter_at(root_fd, "ROUTE.md")
    except (OSError, UnicodeError, ValueError):
        route_body = ""
    destination, destination_heading = _section_content(route_body, "Destination")
    if not destination_heading or not _has_declared_text(destination) or destination.casefold() in {"none", "- none"}:
        issues.append(
            ValidationIssue(
                "handoff-checkpoint",
                "ROUTE.md",
                "Destination must contain a non-empty objective",
            )
        )
    next_action, next_action_heading = _section_content(route_body, "Exact next action")
    if (
        not next_action_heading
        or not _has_declared_text(next_action)
        or next_action.casefold() in {"none", "- none"}
    ):
        issues.append(
            ValidationIssue(
                "handoff-checkpoint",
                "ROUTE.md",
                "Exact next action must be non-empty and canonical",
            )
        )
    try:
        handoff = _read_regular_text_at(root_fd, "HANDOFF.md")
    except (OSError, UnicodeError, ValueError):
        handoff = ""
    intellectual_sections = (
        "Intellectual change",
        "Invalidated assumptions",
        "Live contradiction",
        "Researcher decisions needed",
        "Exact next action and why",
    )
    for heading in intellectual_sections:
        content, present = _section_content(handoff, heading)
        if not present or not _has_declared_text(content):
            issues.append(
                ValidationIssue(
                    "handoff-checkpoint",
                    "HANDOFF.md",
                    f"{heading} must declare content or say - None",
                )
            )
        elif heading == "Exact next action and why" and content.casefold() in {"none", "- none"}:
            issues.append(
                ValidationIssue(
                    "handoff-checkpoint",
                    "HANDOFF.md",
                    "Exact next action and why must contain a next action",
                )
            )
    route_action = (next_action or "").strip()
    handoff_action, _ = _section_content(handoff, "Exact next action and why")
    if (
        route_action
        and route_action.casefold() not in {"none", "- none"}
        and handoff_action
        and route_action.casefold() not in handoff_action.casefold()
    ):
        issues.append(
            ValidationIssue(
                "handoff-checkpoint",
                "HANDOFF.md",
                "handoff exact next action must include the canonical ROUTE.md action",
            )
        )
    return issues


PIPELINE_TERMS = (
    r"\b(?:TwExtract|synthetic_coder|ROUTE\.md|HANDOFF\.md|work-items|"
    r"v\d+(?:\.\d+)*[-\w]*|[A-Z]-X\d+|P[0-3]|D-\d{3})\b",
    r"`[^`\n]*(?:\.md|\.bib|\.csv|\.py)`",
    r"`(?!(?:https?|mailto):)[^`\n]*[/\\][^`\n]*`",
    r"\b(?:references|sources|claims|work-items|literatura)/[^\s`),;]+",
    r"\b(?:S-\d{2}[a-z]?|rr-?\d{3,})\b",
    r"\bsource cards?\b",
    r"\b(?:excerpt|metadata)\s*/\s*(?:excerpt|metadata)\b",
    r"\bpending\s+(?:full[- ]text|page(?:-level)?)\b[^.!?;]{0,80}\bverification\b",
)
RELEASE_SCAFFOLDING = re.compile(
    r"(?i)^\s*(?:\*+Research Route\b|\*?Provisional target\s*:|"
    r"Word count\s*:|Language\s*:|Genre\s*:|"
    r"\*\*(?:Verification note|Preprint|Positionality)\b)"
)
TELEGRAPHIC_TERMS = re.compile(
    r"\b(?:Hecho|Omisión|Fuente|Circularidad|Caso\s+P\d|Aportación\s+metodológica)\b",
    re.IGNORECASE,
)
COMBAT_TERMS = re.compile(
    r"\b(?:primer golpe|desmontar|rompe el hechizo|por eso vende)\b",
    re.IGNORECASE,
)


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        data = archive.read("word/document.xml")
    root = ElementTree.fromstring(data)
    words = [
        node.text or ""
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "t"
    ]
    return " ".join(words)


def _artifact_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _docx_text(path)
    return path.read_text(encoding="utf-8")


def _prose_findings(path: Path, text: str) -> list[ValidationIssue]:
    findings: list[ValidationIssue] = []
    in_code = False
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line):
            continue
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in PIPELINE_TERMS):
            findings.append(
                ValidationIssue(
                    "prose-leak", f"{path.as_posix()}:{line_number}",
                    "internal pipeline identifier appears in publication prose",
                )
            )
        if RELEASE_SCAFFOLDING.search(line):
            findings.append(
                ValidationIssue(
                    "release-scaffolding",
                    f"{path.as_posix()}:{line_number}",
                    "production metadata belongs in the release manifest or title page, not manuscript prose",
                )
            )
        if TELEGRAPHIC_TERMS.search(line):
            findings.append(
                ValidationIssue(
                    "prose-telegraphic", f"{path.as_posix()}:{line_number}",
                    "ledger-like nominal fragment requires an academic sentence",
                )
            )
        if COMBAT_TERMS.search(line):
            findings.append(
                ValidationIssue(
                    "prose-register", f"{path.as_posix()}:{line_number}",
                    "promotional or combative register requires editorial review",
                )
            )
        words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", line)
        if len(words) <= 4 and line.endswith(".") and not re.match(r"^(?:[A-Z][^.!?]+:)$", line):
            findings.append(
                ValidationIssue(
                    "prose-fragment", f"{path.as_posix()}:{line_number}",
                    "very short sentence may be a telegraphic fragment",
                )
            )
    return findings


def _word_count_findings(path: Path, text: str) -> list[ValidationIssue]:
    match = re.search(
        r"(?im)^\s*(?:\*+)?word count\s*:\s*~?([0-9][0-9,]*)\b",
        text,
    )
    if match is None:
        return []
    declared = int(match.group(1).replace(",", ""))
    if declared <= 0:
        return []
    actual = len(re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", text))
    if abs(actual - declared) / declared <= 0.05:
        return []
    line_number = text[: match.start()].count("\n") + 1
    return [
        ValidationIssue(
            "word-count",
            f"{path.as_posix()}:{line_number}",
            f"declared word count {declared} differs from artifact count {actual} by more than 5%",
        )
    ]


def _release_paths(root: Path, release_id: str | None) -> list[Path]:
    if release_id:
        manifest = root / "releases" / release_id / "RELEASE.md"
        if not manifest.is_file():
            return []
        try:
            metadata, _ = parse_frontmatter(manifest)
        except (OSError, UnicodeError, ValueError):
            return []
        paths: list[Path] = []
        for field in ("source_manuscript", "docx"):
            value = metadata.get(field)
            if isinstance(value, str) and value:
                paths.append(root / value)
        return paths
    return sorted(
        path for path in (root / "manuscript").rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".tex", ".docx"}
    )


def _prose_checkpoint_issues(root: Path, release_id: str | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    paths = _release_paths(root, release_id)
    if release_id and not paths:
        return [ValidationIssue("release-manifest", f"releases/{release_id}/RELEASE.md", "release manifest or source manuscript is missing")]
    exceptions_text = ""
    if release_id:
        exceptions = root / "releases" / release_id / "EXCEPTIONS.md"
        if exceptions.is_file():
            exceptions_text = exceptions.read_text(encoding="utf-8")
    for path in paths:
        if not path.is_file():
            issues.append(ValidationIssue("missing-path", _relative_path(root, path), "release artifact is missing"))
            continue
        try:
            artifact = _artifact_text(path)
            artifact_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            for issue in _prose_findings(Path(_relative_path(root, path)), artifact):
                if (
                    issue.code in exceptions_text
                    and issue.path in exceptions_text
                    and artifact_hash in exceptions_text
                ):
                    continue
                issues.append(issue)
            for issue in _word_count_findings(Path(_relative_path(root, path)), artifact):
                if (
                    issue.code in exceptions_text
                    and issue.path in exceptions_text
                    and artifact_hash in exceptions_text
                ):
                    continue
                issues.append(issue)
        except (OSError, UnicodeError, zipfile.BadZipFile, ElementTree.ParseError) as error:
            issues.append(ValidationIssue("artifact-read", _relative_path(root, path), str(error)))
    return issues


def _claim_index_ids(root: Path) -> set[str]:
    path = root / "CLAIMS.md"
    if not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return set()
    return {
        match.group(1)
        for match in re.finditer(
            r"(?im)^\s*-\s*\[?((?:C|S-C)-[0-9]{2,3})\b",
            text,
        )
    }


def _source_card_access(root: Path) -> dict[str, str]:
    cards: dict[str, str] = {}
    sources = root / "sources"
    if not sources.is_dir():
        return cards
    for path in sorted(sources.glob("*.md")):
        match = re.match(r"(S-[0-9]{2}[a-z]?)\b", path.name, re.IGNORECASE)
        if match is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        access = re.search(
            r"(?im)^\s*-\s*access level(?:,[^:\n]+)?\s*:\s*([^|\n]+)",
            text,
        )
        cards[match.group(1).upper()] = access.group(1).strip().casefold() if access else ""
    return cards


def _claim_evidence_issues(
    root: Path,
    path: Path,
    metadata: dict[str, object],
    source_cards: dict[str, str],
    checkpoint: str | None,
) -> list[ValidationIssue]:
    if checkpoint not in {"argument", "release", "submission"}:
        return []
    relative_path = _relative_path(root, path)
    evidence = metadata.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return [
            ValidationIssue(
                "claim-evidence",
                relative_path,
                "evidence must be a non-empty list of source-card references",
            )
        ]
    issues: list[ValidationIssue] = []
    for entry in evidence:
        if not isinstance(entry, str):
            issues.append(
                ValidationIssue(
                    "claim-evidence",
                    relative_path,
                    "each evidence entry must be a source-card reference",
                )
            )
            continue
        ids = {value.upper() for value in SOURCE_ID.findall(entry)}
        if not ids:
            issues.append(
                ValidationIssue(
                    "claim-evidence",
                    relative_path,
                    f"evidence entry has no source-card ID: {entry}",
                )
            )
            continue
        for source_id in sorted(ids):
            if source_id not in source_cards:
                issues.append(
                    ValidationIssue(
                        "missing-source-card",
                        relative_path,
                        f"evidence references missing source card: {source_id}",
                    )
                )
            elif metadata.get("state") == "supported" and not any(
                level in source_cards[source_id]
                for level in ("full text", "dataset", "primary material")
            ):
                issues.append(
                    ValidationIssue(
                        "unsupported-source-access",
                        relative_path,
                        f"supported claim relies on {source_id} without full-text access",
                    )
                )
    return issues


def _orphan_release_artifact_issues(
    root: Path, checkpoint: str | None, release_id: str | None
) -> list[ValidationIssue]:
    if checkpoint not in {"release", "submission"}:
        return []
    referenced: set[Path] = set()
    if release_id:
        manifest = root / "releases" / release_id / "RELEASE.md"
        if manifest.is_file():
            try:
                metadata, _ = parse_frontmatter(manifest)
            except (OSError, UnicodeError, ValueError):
                metadata = {}
            for field in ("source_manuscript", "docx"):
                value = metadata.get(field)
                if isinstance(value, str) and value:
                    referenced.add((root / value).resolve())
    manuscript = root / "manuscript"
    if not manuscript.is_dir():
        return []
    issues: list[ValidationIssue] = []
    for path in sorted(manuscript.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in {".pdf", ".docx", ".html"}:
            continue
        if path.resolve() in referenced:
            continue
        issues.append(
            ValidationIssue(
                "orphan-release-artifact",
                _relative_path(root, path),
                "release artifact is outside a release manifest",
            )
        )
    return issues


def _release_checkpoint_issues(root: Path, release_id: str | None) -> list[ValidationIssue]:
    if not release_id:
        return [ValidationIssue("release-manifest", "releases", "release id is required for release readiness")]
    release_dir = root / "releases" / release_id
    manifest = release_dir / "RELEASE.md"
    if not manifest.is_file():
        return [ValidationIssue("release-manifest", _relative_path(root, manifest), "release manifest is missing")]
    try:
        metadata, _ = parse_frontmatter(manifest)
    except (OSError, UnicodeError, ValueError) as error:
        return [ValidationIssue("release-manifest", _relative_path(root, manifest), str(error))]
    issues: list[ValidationIssue] = []
    source = metadata.get("source_manuscript")
    if not isinstance(source, str) or not source:
        issues.append(ValidationIssue("release-manifest", _relative_path(root, manifest), "source_manuscript is required"))
    elif not (root / source).is_file():
        issues.append(ValidationIssue("missing-path", source, "source manuscript is missing"))
    docx = metadata.get("docx")
    if not isinstance(docx, str) or not docx:
        issues.append(ValidationIssue("release-manifest", _relative_path(root, manifest), "docx is required for release inspection"))
    elif not (root / docx).is_file():
        issues.append(ValidationIssue("missing-path", docx, "DOCX release artifact is missing"))
    if not (release_dir / "APPROVAL.md").is_file():
        issues.append(ValidationIssue("author-approval", _relative_path(root, release_dir / "APPROVAL.md"), "author approval is required for release"))
    return issues


def _v2_semantic_issues(root: Path, checkpoint: str | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    claims_dir = root / "claims"
    claim_paths = sorted(claims_dir.glob("C-*.md")) if claims_dir.is_dir() else []
    index_ids = _claim_index_ids(root)
    structured_ids: set[str] = set()
    source_cards = _source_card_access(root)
    if checkpoint in {"argument", "release", "submission"}:
        if not claim_paths:
            issues.append(
                ValidationIssue(
                    "claims-record",
                    "claims",
                    "argument and release checkpoints require structured claim records",
                )
            )
        if index_ids and not claim_paths:
            issues.append(
                ValidationIssue(
                    "claims-record",
                    "CLAIMS.md",
                    "legacy claims index contains entries without structured claim records",
                )
            )
        if claim_paths and not index_ids:
            issues.append(
                ValidationIssue(
                    "claims-index",
                    "CLAIMS.md",
                    "structured claim records must be listed in CLAIMS.md",
                )
            )
    for path in claim_paths:
        try:
            metadata, body = parse_frontmatter(path)
        except (OSError, UnicodeError, ValueError) as error:
            issues.append(ValidationIssue("invalid-claim-record", _relative_path(root, path), str(error)))
            continue
        claim_id = metadata.get("id")
        if isinstance(claim_id, str):
            structured_ids.add(claim_id)
        required = ("id", "state", "risk", "scope", "evidence", "challenges", "confidence", "manuscript_targets", "review_status", "reopening_condition")
        for field in required:
            if field not in metadata:
                issues.append(ValidationIssue("missing-field", _relative_path(root, path), f"missing claim field: {field}"))
        if metadata.get("state") not in ALLOWED_CLAIM_STATES:
            issues.append(ValidationIssue("invalid-enum", _relative_path(root, path), f"unsupported claim state: {metadata.get('state')!r}"))
        if metadata.get("risk") not in ALLOWED_RISKS:
            issues.append(ValidationIssue("invalid-enum", _relative_path(root, path), f"unsupported claim risk: {metadata.get('risk')!r}"))
        targets = metadata.get("manuscript_targets")
        if "manuscript_targets" in metadata and not isinstance(targets, list):
            issues.append(ValidationIssue("invalid-field", _relative_path(root, path), "manuscript_targets must be a list"))
        if (
            checkpoint in {"release", "submission"}
            and metadata.get("state") in {"provisional", "disputed", "unverified"}
            and isinstance(targets, list)
            and targets
        ):
            issues.append(ValidationIssue("unresolved-manuscript-claim", _relative_path(root, path), "provisional, disputed, or unverified claim cannot target manuscript prose at release"))
        issues.extend(_claim_evidence_issues(root, path, metadata, source_cards, checkpoint))
        if not any(character.isalnum() for character in body):
            issues.append(ValidationIssue("invalid-claim-record", _relative_path(root, path), "claim record must contain a substantive body"))
    if index_ids and structured_ids:
        for claim_id in sorted(index_ids):
            if claim_id.startswith("C-") and claim_id not in structured_ids:
                issues.append(
                    ValidationIssue(
                        "missing-claim-record",
                        "CLAIMS.md",
                        f"claims index entry has no structured record: {claim_id}",
                    )
                )
    if checkpoint in {"argument", "release", "submission"}:
        for path in sorted((root / "work-items").glob("rr-*.md")):
            try:
                metadata, _ = parse_frontmatter(path)
            except (OSError, UnicodeError, ValueError):
                continue
            if metadata.get("review_status") == "deferred" and metadata.get("risk") == "critical":
                issues.append(ValidationIssue("critical-review-deferred", _relative_path(root, path), "critical work cannot be deferred"))
            if checkpoint in {"release", "submission"} and metadata.get("review_status") == "deferred":
                issues.append(ValidationIssue("review-debt", _relative_path(root, path), "deferred review must be resolved before release"))
    return issues


def _parallel_state_issues(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    patterns = re.compile(r"(?i)^(?:CLAIMS|INQUIRY|DECISIONS|OUTLINE|ROUTE|HANDOFF)(?:\s*\d+|[ _-]*(?:copy|copia))\.md$")
    for directory in (root, root / "manuscript"):
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            if path.is_file() and patterns.fullmatch(path.name):
                issues.append(
                    ValidationIssue(
                        "parallel-state",
                        _relative_path(root, path),
                        "parallel state file requires explicit resolution",
                    )
                )
    return issues


def _venue_checkpoint_issues(root: Path, submission: bool = False) -> list[ValidationIssue]:
    venue_file = root / "VENUE.md"
    target_present = False
    if venue_file.is_file():
        try:
            metadata, body = parse_frontmatter(venue_file)
            target_section, present = _section_content(body, "Target")
            target_present = bool(metadata.get("target") or (present and _has_declared_text(target_section)))
        except (OSError, UnicodeError, ValueError):
            body = venue_file.read_text(encoding="utf-8")
            target_section, present = _section_content(body, "Target")
            target_present = bool(present and _has_declared_text(target_section))
    articles = root / "venue" / "articles"
    full_text_count = 0
    if articles.is_dir():
        for path in articles.glob("*.md"):
            try:
                metadata, _ = parse_frontmatter(path)
            except (OSError, UnicodeError, ValueError):
                continue
            if metadata.get("full_text") is True or str(metadata.get("access_level", "")).casefold() == "full text":
                full_text_count += 1
    if venue_file.is_file():
        body = venue_file.read_text(encoding="utf-8")
        match = re.search(r"(?im)full[- ]text(?:s)?\s*[:=]\s*(\d+)", body)
        if match:
            full_text_count = max(full_text_count, int(match.group(1)))
    if not target_present:
        return []
    minimum = 10 if submission else 3
    if full_text_count < minimum:
        return [ValidationIssue("venue-threshold", "VENUE.md", f"venue fingerprint has {full_text_count} full texts; requires {minimum}")]
    return []


def _deferred_items(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in sorted((root / "work-items").glob("rr-*.md")):
        try:
            metadata, _ = parse_frontmatter(path)
        except (OSError, UnicodeError, ValueError):
            continue
        if metadata.get("review_status") == "deferred" or metadata.get("status") == "provisional":
            metadata["path"] = _relative_path(root, path)
            result.append(metadata)
    return result


def review_route(root: Path, stage: str) -> dict[str, object]:
    if stage not in {"argument", "release"}:
        raise ValueError("review stage must be argument or release")
    items = _deferred_items(root)
    critical = [item for item in items if item.get("risk") == "critical"]
    return {
        "stage": stage,
        "deferred_count": len(items),
        "critical_count": len(critical),
        "items": items,
        "ready": not critical if stage == "argument" else not items,
    }


def advance_work(
    root: Path,
    title: str,
    item_type: str,
    owner: str,
    output: str,
    review_later: bool = False,
    risk: str | None = None,
) -> Path:
    if not owner:
        raise ValueError("owner must not be empty")
    route_metadata, _ = parse_frontmatter(root / "ROUTE.md")
    assigned_risk = _requested_risk(item_type, "light", risk)
    if review_later and assigned_risk == "critical":
        raise ValueError("critical work cannot be deferred")
    item = new_work_item(root, title, item_type, "light", [], assigned_risk)
    item_id, _ = parse_frontmatter(item)
    item_id_value = item_id.get("id")
    if not isinstance(item_id_value, str):
        raise ValueError("new work item has no valid id")
    claim_item(root, item_id_value, owner)
    complete_item(
        root,
        item_id_value,
        owner,
        output,
        verification=[] if review_later else [output],
        result=None if review_later else f"Recorded output: {output}",
        provisional=review_later,
    )
    scaffold_handoff(root)
    return item


def migrate_route(root: Path, apply: bool = False) -> dict[str, object]:
    route = root / "ROUTE.md"
    metadata, _ = parse_frontmatter(route)
    source_version = _schema_version(metadata)
    report: dict[str, object] = {"from": source_version, "to": 2, "apply": apply, "changes": []}
    if source_version == 2:
        report["changes"] = ["already-v2"]
        return report
    if source_version != 1:
        raise ValueError(f"unsupported source schema: {source_version}")
    changes = ["ROUTE.md schema_version: 1 -> 2", "add claims/ and releases/", "add v2 work-item risk and review_status"]
    cycle = metadata.get("current_cycle")
    if cycle in {"refine", "polish"}:
        changes.append(f"current_cycle: {cycle} -> audit")
    report["changes"] = changes
    if not apply:
        return report
    backup_dir = root / ".research-route" / "migrations" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(route, backup_dir / "ROUTE.md")
    handoff = root / "HANDOFF.md"
    if handoff.is_file():
        shutil.copy2(handoff, backup_dir / "HANDOFF.md")
    (root / "claims").mkdir(exist_ok=True)
    (root / "releases").mkdir(exist_ok=True)
    metadata["schema_version"] = 2
    if cycle in {"refine", "polish"}:
        metadata["current_cycle"] = "audit"
    route_body = parse_frontmatter(route)[1]
    write_frontmatter(route, metadata, route_body)
    for path in sorted((root / "work-items").glob("rr-*.md")):
        item_metadata, body = parse_frontmatter(path)
        shutil.copy2(path, backup_dir / path.name)
        item_metadata["schema_version"] = 2
        item_metadata.setdefault("risk", _risk_for_item(str(item_metadata.get("type", "question")), str(item_metadata.get("mode", "light"))))
        item_metadata.setdefault("review_status", "none")
        item_metadata.setdefault("acceptance", ["Record a defensible result and link its canonical output."])
        item_metadata.setdefault("verification", [])
        item_metadata.setdefault("result", None)
        write_frontmatter(path, item_metadata, body)
    if (root / "CLAIMS.md").is_file() and (root / "CLAIMS.md").read_text(encoding="utf-8").strip():
        migration_note = root / "claims" / "MIGRATION-REVIEW.md"
        migration_note.write_text(
            "---\nschema_version: 2\nmigration_status: needs_review\n---\n\n# Claims migration\n\nReview legacy CLAIMS.md and create one structured claim record per substantive claim.\n",
            encoding="utf-8",
        )
    try:
        scaffold_handoff(root)
        changes.append("regenerate HANDOFF.md")
    except (OSError, UnicodeError, ValueError) as error:
        report["handoff_warning"] = str(error)
    return report


def approve_release_record(
    root: Path, release_id: str, kind: str, values: dict[str, str]
) -> Path:
    release_dir = root / "releases" / release_id
    manifest = release_dir / "RELEASE.md"
    if not manifest.is_file():
        raise ValueError(f"release manifest is missing: {manifest}")
    release_dir.mkdir(parents=True, exist_ok=True)
    target = release_dir / ("EXCEPTIONS.md" if kind == "exceptions" else "APPROVAL.md")
    lines = [f"# Release {kind.title()}", ""]
    for key, value in values.items():
        lines.append(f"- {key}: {value}")
    try:
        manifest_metadata, _ = parse_frontmatter(manifest)
        source = manifest_metadata.get("source_manuscript")
        if isinstance(source, str) and (root / source).is_file():
            lines.append(
                f"- artifact_sha256: {hashlib.sha256((root / source).read_bytes()).hexdigest()}"
            )
    except (OSError, UnicodeError, ValueError):
        pass
    lines.append(f"- timestamp: {datetime.now(timezone.utc).isoformat()}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def validate_route(
    root: Path, checkpoint: str | None = None, release_id: str | None = None
) -> list[ValidationIssue]:
    if checkpoint not in {
        None,
        "handoff",
        "argument",
        "research",
        "venue",
        "prose",
        "release",
        "submission",
    }:
        raise ValueError(f"unsupported validation checkpoint: {checkpoint}")
    try:
        root_fd = os.open(root, DIRECTORY_FLAGS)
    except OSError:
        return [ValidationIssue("missing-path", ".", "research route root is missing")]
    try:
        try:
            with _directory_at(root_fd, ".research-route", missing_ok=True) as state_fd:
                return _validate_route_at(root, root_fd, state_fd, checkpoint, release_id)
        except ValueError:
            issues = _validate_route_at(root, root_fd, None, checkpoint, release_id)
            issues.append(
                ValidationIssue(
                    "invalid-claim",
                    ".research-route",
                    "state path must be a regular, non-symlinked directory",
                )
            )
            return sorted(
                issues, key=lambda issue: (issue.path, issue.code, issue.message)
            )
    finally:
        os.close(root_fd)


def _validate_route_at(
    root: Path,
    root_fd: int,
    state_fd: int | None,
    checkpoint: str | None,
    release_id: str | None = None,
) -> list[ValidationIssue]:
    try:
        work_items_fd = os.open("work-items", DIRECTORY_FLAGS, dir_fd=root_fd)
    except OSError:
        return _validate_route_contents_at(root, root_fd, state_fd, None, checkpoint, release_id)
    try:
        return _validate_route_contents_at(root, root_fd, state_fd, work_items_fd, checkpoint, release_id)
    finally:
        os.close(work_items_fd)


def _validate_route_contents_at(
    root: Path,
    root_fd: int,
    state_fd: int | None,
    work_items_fd: int | None,
    checkpoint: str | None,
    release_id: str | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for relative_path in REQUIRED_FILES:
        if not stat.S_ISREG(_relative_kind_at(root_fd, relative_path) or 0):
            issues.append(
                ValidationIssue(
                    "missing-path", relative_path, "required file is missing"
                )
            )
    for relative_path in REQUIRED_DIRECTORIES:
        exists = (
            work_items_fd is not None
            if relative_path == "work-items"
            else stat.S_ISDIR(_relative_kind_at(root_fd, relative_path) or 0)
        )
        if not exists:
            issues.append(
                ValidationIssue(
                    "missing-path", relative_path, "required directory is missing"
                )
            )

    route_metadata_for_scope: dict[str, object] = {}
    if stat.S_ISREG(_relative_kind_at(root_fd, "ROUTE.md") or 0):
        try:
            route_metadata_for_scope, _ = _parse_frontmatter_at(root_fd, "ROUTE.md")
        except (OSError, UnicodeError, ValueError):
            route_metadata_for_scope = {}
    if _is_v2_root(route_metadata_for_scope):
        for relative_path in ("claims", "releases"):
            if not stat.S_ISDIR(_relative_kind_at(root_fd, relative_path) or 0):
                issues.append(
                    ValidationIssue(
                        "missing-path", relative_path, "required v2 directory is missing"
                    )
                )

    route_path = Path("ROUTE.md")
    if stat.S_ISREG(_relative_kind_at(root_fd, "ROUTE.md") or 0):
        try:
            route_metadata, _ = _parse_frontmatter_at(root_fd, "ROUTE.md")
        except (OSError, UnicodeError, ValueError) as error:
            issues.append(
                ValidationIssue("invalid-frontmatter", "ROUTE.md", str(error))
            )
        else:
            _missing_fields(
                issues, root, route_path, route_metadata, ROUTE_FIELDS
            )
            for field in ("project_title", "language"):
                value = route_metadata.get(field)
                if field in route_metadata and (
                    not isinstance(value, str) or not value.strip()
                ):
                    issues.append(
                        ValidationIssue(
                            "invalid-field",
                            "ROUTE.md",
                            f"{field} must be a non-empty string",
                        )
                    )
            for field in ("target_venue", "fallback_venue"):
                value = route_metadata.get(field)
                if value is not None and not isinstance(value, str):
                    issues.append(
                        ValidationIssue(
                            "invalid-field",
                            "ROUTE.md",
                            f"{field} must be a string or null",
                        )
                    )
            schema_version = route_metadata.get("schema_version")
            if schema_version not in ALLOWED_SCHEMA_VERSIONS:
                issues.append(
                    ValidationIssue(
                        "unsupported-schema",
                        "ROUTE.md",
                        f"unsupported schema_version: {schema_version!r}",
                    )
                )
            cycle = route_metadata.get("current_cycle")
            if "current_cycle" in route_metadata and (
                not isinstance(cycle, str) or cycle not in ALLOWED_CYCLES
            ):
                issues.append(
                    ValidationIssue(
                        "invalid-enum",
                        "ROUTE.md",
                        f"unsupported current_cycle: {cycle!r}",
                    )
                )
            counter = route_metadata.get("next_work_item")
            if counter is not None and (type(counter) is not int or counter < 1):
                issues.append(
                    ValidationIssue(
                        "invalid-field",
                        "ROUTE.md",
                        "next_work_item must be a positive integer",
                    )
                )

    items_by_id: dict[str, list[Path]] = {}
    item_records_by_id: dict[str, list[dict[str, object]]] = {}
    dependencies_by_id: dict[str, list[str]] = {}
    if work_items_fd is not None:
        for name in sorted(
            entry for entry in os.listdir(work_items_fd) if entry.endswith(".md")
        ):
            relative_path = f"work-items/{name}"
            if not stat.S_ISREG(
                os.stat(name, dir_fd=work_items_fd, follow_symlinks=False).st_mode
            ):
                continue
            try:
                metadata, body = _parse_frontmatter_at(
                    work_items_fd, name, root / relative_path
                )
            except (OSError, UnicodeError, ValueError) as error:
                issues.append(
                    ValidationIssue("invalid-frontmatter", relative_path, str(error))
                )
                continue
            record_errors = _work_item_record_errors(metadata)
            issues.extend(
                ValidationIssue(code, relative_path, message)
                for code, message in record_errors
            )
            issues.extend(
                ValidationIssue(code, relative_path, message)
                for code, message in _work_item_section_errors(body)
            )
            item_id = metadata.get("id")
            if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id):
                continue
            path = Path(relative_path)
            items_by_id.setdefault(item_id, []).append(path)
            item_records_by_id.setdefault(item_id, []).append(metadata)
            if not name.startswith(f"{item_id}-"):
                issues.append(
                    ValidationIssue(
                        "item-id-mismatch",
                        relative_path,
                        f"filename does not match work-item id {item_id}",
                    )
                )
            dependencies = metadata.get("depends_on")
            if isinstance(dependencies, list) and all(
                isinstance(dependency, str) and ITEM_ID.fullmatch(dependency)
                for dependency in dependencies
            ):
                dependencies_by_id.setdefault(item_id, []).extend(dependencies)

    issues.extend(_duplicate_item_issues(root, items_by_id))
    known_ids = set(items_by_id)
    unique_items = {
        item_id: records[0]
        for item_id, records in item_records_by_id.items()
        if len(records) == 1
    }
    for item_id, dependencies in sorted(dependencies_by_id.items()):
        for dependency in sorted(set(dependencies) - known_ids):
            for path in items_by_id[item_id]:
                issues.append(
                    ValidationIssue(
                        "missing-dependency",
                        _relative_path(root, path),
                        f"dependency does not exist: {dependency}",
                    )
                )
    graph = {
        item_id: sorted(set(dependencies))
        for item_id, dependencies in dependencies_by_id.items()
    }
    for cycle in _dependency_cycles(graph):
        cycle_text = " -> ".join((*cycle, cycle[0]))
        for item_id in cycle:
            for path in items_by_id[item_id]:
                issues.append(
                    ValidationIssue(
                        "dependency-cycle",
                        _relative_path(root, path),
                        f"dependency cycle: {cycle_text}",
                    )
                )

    if state_fd is not None:
        try:
            with _directory_at(state_fd, "claims", missing_ok=True) as claims_fd:
                if claims_fd is not None:
                    for name in sorted(
                        entry
                        for entry in os.listdir(claims_fd)
                        if entry.endswith(".lock")
                    ):
                        relative_path = f".research-route/claims/{name}"
                        filename_id = name.removesuffix(".lock")
                        try:
                            claim = json.loads(
                                _read_regular_text_at(claims_fd, name)
                            )
                        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
                            issues.append(
                                ValidationIssue("invalid-claim", relative_path, str(error))
                            )
                            continue
                        for message in _claim_record_errors(claim):
                            issues.append(
                                ValidationIssue("invalid-claim", relative_path, message)
                            )
                        if not isinstance(claim, dict):
                            continue
                        issues.extend(
                            ValidationIssue(code, relative_path, message)
                            for code, message in _claim_identity_errors(claim, filename_id)
                        )
                        issues.extend(
                            ValidationIssue(code, relative_path, message)
                            for code, message in _claim_reference_errors(
                                claim, filename_id, known_ids
                            )
                        )
                        issues.extend(
                            ValidationIssue("incompatible-claim", relative_path, message)
                            for message in _claim_compatibility_errors(claim, unique_items)
                        )
        except ValueError:
            issues.append(
                ValidationIssue(
                    "invalid-claim",
                    ".research-route/claims",
                    "claims path must be a regular, non-symlinked directory",
                )
            )
    if stat.S_ISREG(_relative_kind_at(root_fd, "ROUTE.md") or 0):
        handoff_issue = _handoff_freshness_issue(root_fd)
        if handoff_issue is not None:
            issues.append(handoff_issue)
    privacy_issue = _privacy_issue(root_fd)
    if privacy_issue is not None:
        issues.append(privacy_issue)
    if checkpoint == "handoff":
        issues.extend(_handoff_checkpoint_issues(root_fd))
    if _is_v2_root(route_metadata_for_scope):
        issues.extend(_v2_semantic_issues(root, checkpoint))
        issues.extend(_parallel_state_issues(root))
    if checkpoint in {"prose", "release", "submission"}:
        issues.extend(_prose_checkpoint_issues(root, release_id))
    if checkpoint in {"venue", "submission"}:
        issues.extend(_venue_checkpoint_issues(root, checkpoint == "submission"))
    if checkpoint in {"release", "submission"}:
        issues.extend(_orphan_release_artifact_issues(root, checkpoint, release_id))
        issues.extend(_release_checkpoint_issues(root, release_id))
    _validate_markdown_links(root_fd, issues, work_items_fd)
    return sorted(issues, key=lambda issue: (issue.path, issue.code, issue.message))


def init_route(
    destination: Path, title: str, language: str, schema_version: int = PROJECT_SCHEMA_VERSION
) -> Path:
    if schema_version not in ALLOWED_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported schema version: {schema_version}")
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
        metadata["schema_version"] = schema_version
        metadata["project_title"] = title
        metadata["language"] = language
        write_frontmatter(staged_route, metadata, body)
        staging.replace(destination)
        return destination / "ROUTE.md"
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _scaffold_handoff_locked(root: Path, root_fd: int, state_fd: int) -> Path:
    _require_file_at(root_fd, root, "ROUTE.md")
    metadata, route_body, route_signature = _read_route_snapshot(root_fd)
    _require_file_at(root_fd, root, "HANDOFF.md")
    original = _read_regular_text_at(root_fd, "HANDOFF.md").encode("utf-8")
    if original.count(HANDOFF_BEGIN) != 1 or original.count(HANDOFF_END) != 1:
        raise ValueError("HANDOFF.md must contain exactly one mechanical marker pair")
    prefix, remainder = original.split(HANDOFF_BEGIN, 1)
    _, suffix = remainder.split(HANDOFF_END, 1)

    items: list[dict[str, object]] = []
    items_by_id: dict[str, list[Path]] = {}
    with _directory_at(root_fd, "work-items") as work_items_fd:
        assert work_items_fd is not None
        for name in sorted(
            entry for entry in os.listdir(work_items_fd) if entry.endswith(".md")
        ):
            item_path = root / "work-items" / name
            try:
                item_metadata, _ = _parse_frontmatter_at(
                    work_items_fd, name, item_path
                )
            except ValueError as error:
                raise ValueError(f"invalid work item {item_path}: {error}") from None
            record_errors = _work_item_record_errors(item_metadata)
            if record_errors:
                raise ValueError(
                    f"invalid work item {item_path}: {record_errors[0][1]}"
                )
            items.append(item_metadata)
            item_id = item_metadata["id"]
            assert isinstance(item_id, str)
            items_by_id.setdefault(item_id, []).append(Path("work-items") / name)

    duplicate_issues = _duplicate_item_issues(root, items_by_id)
    if duplicate_issues:
        raise ValueError(f"ambiguous work items: {duplicate_issues[0].message}")
    known_ids = set(items_by_id)
    item_records = {
        item_id: item
        for item in items
        if isinstance((item_id := item.get("id")), str)
    }
    statuses = {item.get("id"): item.get("status") for item in items}
    active_claims: list[str] = []
    claimed_next_actions: list[str] = []
    claimed_ids: set[object] = set()
    with _directory_at(state_fd, "claims", missing_ok=True) as claims_fd:
        if claims_fd is not None:
            for name in sorted(
                entry for entry in os.listdir(claims_fd) if entry.endswith(".lock")
            ):
                path = root / ".research-route" / "claims" / name
                claim = json.loads(_read_regular_text_at(claims_fd, name))
                claim_errors = _claim_record_errors(claim)
                if claim_errors:
                    raise ValueError(f"invalid claim {path}: {claim_errors[0]}")
                assert isinstance(claim, dict)
                filename_id = name.removesuffix(".lock")
                identity_errors = _claim_identity_errors(claim, filename_id)
                if identity_errors:
                    raise ValueError(f"invalid claim {path}: {identity_errors[0][1]}")
                reference_errors = _claim_reference_errors(
                    claim, filename_id, known_ids
                )
                if reference_errors:
                    raise ValueError(
                        f"invalid claim {path}: {reference_errors[0][1]}"
                    )
                compatibility_errors = _claim_compatibility_errors(
                    claim, item_records
                )
                if compatibility_errors:
                    raise ValueError(
                        f"incompatible claim {path}: {compatibility_errors[0]}"
                    )
                claimed_ids.add(claim.get("item_id"))
                active_claims.append(
                    f"- {claim.get('item_id')}: {claim.get('owner')}"
                )
                item = next(
                    item for item in items if item.get("id") == claim.get("item_id")
                )
                if item.get("status") == "open" and all(
                    statuses.get(dependency) == "closed"
                    for dependency in item.get("depends_on", [])
                ):
                    claimed_next_actions.append(
                        f"- Continue {claim.get('item_id')}: {item.get('title')} "
                        f"(owner: {claim.get('owner')})"
                    )

    open_items = [
        f"- {item.get('id')}: {item.get('title')}"
        for item in items
        if item.get("status") == "open"
        and item.get("id") not in claimed_ids
        and isinstance(item.get("depends_on"), list)
        and all(
            statuses.get(dependency) == "closed"
            for dependency in item["depends_on"]
        )
    ]
    deferred_review = [
        f"- {item.get('id')}: {item.get('title')} (risk: {item.get('risk', 'legacy')})"
        for item in items
        if item.get("review_status") == "deferred" or item.get("status") == "provisional"
    ]

    generated_at = datetime.now(timezone.utc).isoformat()
    route_modified = datetime.fromtimestamp(
        route_signature[3] / 1_000_000_000, timezone.utc
    ).isoformat()
    blocks_match = re.search(
        r"(?ms)^## Blocks[ \t]*\r?\n(.*?)(?=^## |\Z)", route_body
    )
    blocks = blocks_match.group(1).strip() if blocks_match else ""
    exact_action_match = re.search(
        r"(?ms)^## Exact next action[ \t]*\r?\n(.*?)(?=^## |\Z)", route_body
    )
    exact_action = exact_action_match.group(1).strip() if exact_action_match else ""
    if exact_action and exact_action.lower() not in {"none", "- none"}:
        next_action = exact_action
    elif blocks and blocks.lower() not in {"none", "- none"}:
        next_action = (
            "- Resolve the blocking conditions recorded in ROUTE.md before "
            "continuing work."
        )
    elif claimed_next_actions:
        next_action = claimed_next_actions[0]
    elif open_items:
        next_action = open_items[0].replace("- ", "- Start ", 1)
    else:
        next_action = "- Ask the researcher to define the next work item."
    mechanical = (
        "\n\n"
        f"- Project: {metadata.get('project_title')}\n"
        f"- Schema version: {metadata.get('schema_version')}\n"
        f"- Current cycle: {metadata.get('current_cycle')}\n"
        f"- Target venue: {metadata.get('target_venue')}\n"
        f"- Fallback venue: {metadata.get('fallback_venue')}\n"
        f"- Generated at: {generated_at}\n"
        f"- ROUTE.md modified: {route_modified}\n\n"
        "### Open frontier candidates\n\n"
        + ("\n".join(open_items) if open_items else "- None")
        + "\n\n### Active claims\n\n"
        + ("\n".join(active_claims) if active_claims else "- None")
        + "\n\n### Deferred review\n\n"
        + ("\n".join(deferred_review) if deferred_review else "- None")
        + "\n\n### Blocks\n\n"
        + (blocks if blocks else "- None")
        + "\n\n### Exact next action\n\n"
        + next_action
        + "\n\n"
    ).encode("utf-8")
    if not _route_snapshot_is_current(root_fd, route_signature):
        raise ValueError("ROUTE.md changed while generating handoff")
    _atomic_write_bytes_at(
        root_fd,
        "HANDOFF.md",
        prefix + HANDOFF_BEGIN + mechanical + HANDOFF_END + suffix,
        lambda: _route_snapshot_is_current(root_fd, route_signature),
    )
    if not _route_snapshot_is_current(root_fd, route_signature):
        raise _PublishedStaleHandoff
    return root / "HANDOFF.md"


def scaffold_handoff(root: Path) -> Path:
    with _state_directory_fd(root, create=True) as (root_fd, state_fd):
        assert state_fd is not None
        with _claim_guard(state_fd):
            for attempt in range(3):
                try:
                    return _scaffold_handoff_locked(root, root_fd, state_fd)
                except _PublishedStaleHandoff:
                    if attempt == 2:
                        raise ValueError(
                            "ROUTE.md kept changing after handoff publication"
                        ) from None
    raise AssertionError("unreachable")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="route.py")
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="{init,new,claim,release,complete,advance,review,validate,handoff}",
    )
    init_parser = commands.add_parser("init")
    init_parser.add_argument("destination", type=Path)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--language", required=True)
    init_parser.add_argument(
        "--schema-version", type=int, choices=sorted(ALLOWED_SCHEMA_VERSIONS), default=LEGACY_SCHEMA_VERSION
    )
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
    new_parser.add_argument("--risk", choices=sorted(ALLOWED_RISKS))
    claim_parser = commands.add_parser("claim")
    claim_parser.add_argument("item_id")
    claim_parser.add_argument("--root", type=Path, required=True)
    claim_parser.add_argument("--owner", required=True)
    release_parser = commands.add_parser("release")
    release_parser.add_argument("item_id")
    release_parser.add_argument("--root", type=Path, required=True)
    release_parser.add_argument("--owner", required=True)
    release_parser.add_argument("--force", action="store_true")
    complete_parser = commands.add_parser(
        "complete", help="close an owned work item and persist its output"
    )
    complete_parser.add_argument("item_id")
    complete_parser.add_argument("--root", type=Path, required=True)
    complete_parser.add_argument("--owner", required=True)
    complete_parser.add_argument("--output", required=True)
    complete_parser.add_argument("--provisional", action="store_true")
    complete_parser.add_argument("--verification", action="append", default=[])
    complete_parser.add_argument("--result")
    advance_parser = commands.add_parser(
        "advance", help="record a compact result through the adaptive route"
    )
    advance_parser.add_argument("--root", type=Path, required=True)
    advance_parser.add_argument("--title", required=True)
    advance_parser.add_argument(
        "--type", dest="item_type", choices=sorted(ALLOWED_ITEM_TYPES), required=True
    )
    advance_parser.add_argument("--owner", required=True)
    advance_parser.add_argument("--output", required=True)
    advance_parser.add_argument("--review-later", action="store_true")
    advance_parser.add_argument("--risk", choices=sorted(ALLOWED_RISKS))
    review_parser = commands.add_parser("review", help="report grouped review debt")
    review_parser.add_argument("--root", type=Path, required=True)
    review_parser.add_argument("--stage", choices=("argument", "release"), required=True)
    migrate_parser = commands.add_parser("migrate", help=argparse.SUPPRESS)
    migrate_parser.add_argument("--root", type=Path, required=True)
    migrate_parser.add_argument("--to", type=int, choices=(2,), required=True)
    migrate_parser.add_argument("--dry-run", action="store_true")
    migrate_parser.add_argument("--apply", action="store_true")
    exception_parser = commands.add_parser("approve-exception")
    exception_parser.add_argument("--root", type=Path, required=True)
    exception_parser.add_argument("--release", required=True)
    exception_parser.add_argument("--finding", required=True)
    exception_parser.add_argument("--author", required=True)
    exception_parser.add_argument("--rationale", required=True)
    approval_parser = commands.add_parser("approve-release")
    approval_parser.add_argument("--root", type=Path, required=True)
    approval_parser.add_argument("--release", required=True)
    approval_parser.add_argument("--author", required=True)
    approval_parser.add_argument("--decision", required=True)
    validate_parser = commands.add_parser(
        "validate", help="check structural integrity; use --checkpoint handoff for transfer readiness"
    )
    validate_parser.add_argument("--root", type=Path, required=True)
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.add_argument(
        "--checkpoint",
        choices=("handoff", "argument", "research", "venue", "prose", "release", "submission"),
        help="run a focused deterministic readiness check",
    )
    validate_parser.add_argument("--release", dest="release_id")
    handoff_parser = commands.add_parser("handoff")
    handoff_parser.add_argument("--root", type=Path, required=True)
    # Keep the compatibility migration command callable without advertising it
    # in the v1 help contract.
    commands._choices_actions = [
        action for action in commands._choices_actions if action.dest != "migrate"
    ]
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "init":
            init_route(
                arguments.destination,
                arguments.title,
                arguments.language,
                arguments.schema_version,
            )
        elif arguments.command == "new":
            new_work_item(
                arguments.root,
                arguments.title,
                arguments.item_type,
                arguments.mode,
                arguments.depends_on,
                arguments.risk,
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
        elif arguments.command == "complete":
            if arguments.provisional:
                item_files = sorted((arguments.root / "work-items").glob(f"{arguments.item_id}-*.md"))
                if len(item_files) != 1:
                    raise ValueError(f"work item is ambiguous or missing: {arguments.item_id}")
                item_metadata, _ = parse_frontmatter(item_files[0])
                if item_metadata.get("risk") == "critical":
                    raise ValueError("critical work cannot be deferred")
            complete_item(
                arguments.root,
                arguments.item_id,
                arguments.owner,
                arguments.output,
                arguments.verification,
                arguments.result,
                arguments.provisional,
            )
            if arguments.provisional:
                item_files = sorted((arguments.root / "work-items").glob(f"{arguments.item_id}-*.md"))
                if len(item_files) != 1:
                    raise ValueError(f"work item is ambiguous or missing: {arguments.item_id}")
                item_file = item_files[0]
                metadata, body = parse_frontmatter(item_file)
                metadata["status"] = "provisional"
                if metadata.get("schema_version") == 2:
                    metadata["review_status"] = "deferred"
                write_frontmatter(item_file, metadata, body)
            elif arguments.verification or arguments.result is not None:
                item_files = sorted((arguments.root / "work-items").glob(f"{arguments.item_id}-*.md"))
                if len(item_files) != 1:
                    raise ValueError(f"work item is ambiguous or missing: {arguments.item_id}")
                item_file = item_files[0]
                metadata, body = parse_frontmatter(item_file)
                if metadata.get("schema_version") == 2:
                    metadata["verification"] = arguments.verification
                    metadata["result"] = arguments.result
                    metadata["review_status"] = "reviewed"
                    write_frontmatter(item_file, metadata, body)
        elif arguments.command == "advance":
            advance_work(
                arguments.root,
                arguments.title,
                arguments.item_type,
                arguments.owner,
                arguments.output,
                arguments.review_later,
                arguments.risk,
            )
        elif arguments.command == "review":
            print(json.dumps(review_route(arguments.root, arguments.stage), ensure_ascii=False))
        elif arguments.command == "migrate":
            if arguments.dry_run == arguments.apply:
                raise ValueError("choose exactly one of --dry-run or --apply")
            marker = arguments.root / ".research-route" / "migration-v2-dry-run.json"
            if arguments.dry_run:
                report = migrate_route(arguments.root, False)
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(
                    json.dumps(
                        {
                            "route_sha256": hashlib.sha256(
                                (arguments.root / "ROUTE.md").read_bytes()
                            ).hexdigest(),
                            "report": report,
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            else:
                if not marker.is_file():
                    raise ValueError("run migrate --dry-run before --apply")
                try:
                    marker_data = json.loads(marker.read_text(encoding="utf-8"))
                    current_hash = hashlib.sha256(
                        (arguments.root / "ROUTE.md").read_bytes()
                    ).hexdigest()
                except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
                    raise ValueError(f"invalid migration dry-run marker: {error}") from None
                if marker_data.get("route_sha256") != current_hash:
                    raise ValueError("ROUTE.md changed after migration dry-run; rerun --dry-run")
                report = migrate_route(arguments.root, True)
                marker.unlink()
            print(json.dumps(report, ensure_ascii=False))
        elif arguments.command == "approve-exception":
            approve_release_record(
                arguments.root,
                arguments.release,
                "exceptions",
                {"finding": arguments.finding, "author": arguments.author, "rationale": arguments.rationale},
            )
        elif arguments.command == "approve-release":
            approve_release_record(
                arguments.root,
                arguments.release,
                "approval",
                {"author": arguments.author, "decision": arguments.decision},
            )
        elif arguments.command == "validate":
            issues = validate_route(arguments.root, arguments.checkpoint, arguments.release_id)
            if arguments.json:
                print(json.dumps([asdict(issue) for issue in issues], ensure_ascii=False))
            else:
                for issue in issues:
                    print(f"{issue.path}: {issue.code}: {issue.message}")
            return 1 if issues else 0
        elif arguments.command == "handoff":
            scaffold_handoff(arguments.root)
    except (FileExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
