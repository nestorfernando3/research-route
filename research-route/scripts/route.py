from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
import posixpath
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Callable, Iterator


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
ALLOWED_STATUSES = {"open", "closed"}
ALLOWED_CYCLES = {"discover", "argue", "compose", "audit"}
PROJECT_SCHEMA_VERSION = 1
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
            _parse_frontmatter_at(root_fd, "ROUTE.md")
            with _directory_at(root_fd, "work-items") as work_items_fd:
                assert work_items_fd is not None
                item_id = _reserve_item_id(root_fd, work_items_fd, state_fd)
                item_name = f"{item_id}-{slug}.md"
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
                    if item.get("status") != "open":
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
                        if dependency_item.get("status") != "closed":
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


def complete_item(root: Path, item_id: str, owner: str, output: str) -> Path:
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
                    if item.get("status") != "open":
                        raise ValueError(f"unsupported work-item status: {item.get('status')}")
                    item["status"] = "closed"
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
    errors: list[tuple[str, str]] = [
        ("missing-field", f"missing required field: {field}")
        for field in sorted(ITEM_FIELDS - metadata.keys())
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
    schema_version = metadata.get("schema_version")
    if schema_version != PROJECT_SCHEMA_VERSION:
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
    return issues


def validate_route(root: Path, checkpoint: str | None = None) -> list[ValidationIssue]:
    if checkpoint not in {None, "handoff"}:
        raise ValueError(f"unsupported validation checkpoint: {checkpoint}")
    try:
        root_fd = os.open(root, DIRECTORY_FLAGS)
    except OSError:
        return [ValidationIssue("missing-path", ".", "research route root is missing")]
    try:
        try:
            with _directory_at(root_fd, ".research-route", missing_ok=True) as state_fd:
                return _validate_route_at(root, root_fd, state_fd, checkpoint)
        except ValueError:
            issues = _validate_route_at(root, root_fd, None, checkpoint)
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
    root: Path, root_fd: int, state_fd: int | None, checkpoint: str | None
) -> list[ValidationIssue]:
    try:
        work_items_fd = os.open("work-items", DIRECTORY_FLAGS, dir_fd=root_fd)
    except OSError:
        return _validate_route_contents_at(root, root_fd, state_fd, None, checkpoint)
    try:
        return _validate_route_contents_at(root, root_fd, state_fd, work_items_fd, checkpoint)
    finally:
        os.close(work_items_fd)


def _validate_route_contents_at(
    root: Path,
    root_fd: int,
    state_fd: int | None,
    work_items_fd: int | None,
    checkpoint: str | None,
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
            if schema_version != PROJECT_SCHEMA_VERSION:
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
    _validate_markdown_links(root_fd, issues, work_items_fd)
    return sorted(issues, key=lambda issue: (issue.path, issue.code, issue.message))


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
    complete_parser = commands.add_parser(
        "complete", help="close an owned work item and persist its output"
    )
    complete_parser.add_argument("item_id")
    complete_parser.add_argument("--root", type=Path, required=True)
    complete_parser.add_argument("--owner", required=True)
    complete_parser.add_argument("--output", required=True)
    validate_parser = commands.add_parser(
        "validate", help="check structural integrity; use --checkpoint handoff for transfer readiness"
    )
    validate_parser.add_argument("--root", type=Path, required=True)
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.add_argument(
        "--checkpoint", choices=("handoff",), help="run deterministic handoff readiness checks"
    )
    handoff_parser = commands.add_parser("handoff")
    handoff_parser.add_argument("--root", type=Path, required=True)
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
        elif arguments.command == "complete":
            complete_item(
                arguments.root,
                arguments.item_id,
                arguments.owner,
                arguments.output,
            )
        elif arguments.command == "validate":
            issues = validate_route(arguments.root, arguments.checkpoint)
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
