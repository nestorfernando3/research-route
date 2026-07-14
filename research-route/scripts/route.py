from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import json
import os
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


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class MigrationPlan:
    current_version: int
    target_version: int
    changes: tuple[str, ...]
    applicable: bool


Migration = Callable[[Path, bool], tuple[str, ...]]
MIGRATIONS: dict[tuple[int, int], Migration] = {}


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
        temporary_path.chmod(mode)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


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
    if create:
        path.mkdir(exist_ok=True)
    elif not path.exists():
        raise ValueError(f"missing directory: {path}")
    if path.is_symlink():
        raise ValueError(f"symlinked directory is not allowed: {path}")
    if not path.is_dir():
        raise ValueError(f"expected directory: {path}")
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
    return tuple(errors)


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


def _broken_markdown_target(path: Path, destination: str) -> bool:
    lowered = destination.lower()
    if (
        not destination
        or destination.startswith("#")
        or lowered.startswith(("http:", "https:", "mailto:"))
        or destination.startswith("/")
    ):
        return False
    target_text = destination.partition("#")[0].partition("?")[0]
    return bool(target_text and not (path.parent / target_text).exists())


def _validate_markdown_links(
    root: Path, issues: list[ValidationIssue]
) -> None:
    for path in sorted(root.rglob("*.md")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(
                ValidationIssue(
                    "unreadable-file", _relative_path(root, path), str(error)
                )
            )
            continue
        for match in MARKDOWN_LINK.finditer(text):
            destination = match.group(1).strip()
            if destination.startswith("<") and ">" in destination:
                destination = destination[1 : destination.index(">")]
            else:
                destination = destination.split(maxsplit=1)[0]
            if _broken_markdown_target(path, destination):
                issues.append(
                    ValidationIssue(
                        "broken-link",
                        _relative_path(root, path),
                        f"relative link does not exist: {destination}",
                    )
                )
        definitions: dict[str, str] = {}
        for match in REFERENCE_DEFINITION.finditer(text):
            label = _reference_label(match.group(1))
            definitions.setdefault(label, match.group(2) or match.group(3))
        references = {
            _reference_label(match.group(2) or match.group(1))
            for match in REFERENCE_LINK.finditer(text)
        }
        references.update(
            label
            for match in SHORTCUT_REFERENCE.finditer(text)
            if (label := _reference_label(match.group(1))) in definitions
        )
        for label in sorted(references):
            destination = definitions.get(label)
            if destination is None:
                issues.append(
                    ValidationIssue(
                        "broken-link",
                        _relative_path(root, path),
                        f"reference definition does not exist: {label}",
                    )
                )
            elif _broken_markdown_target(path, destination):
                issues.append(
                    ValidationIssue(
                        "broken-link",
                        _relative_path(root, path),
                        f"relative link does not exist: {destination}",
                    )
                )


def validate_route(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if root.is_symlink() or not root.is_dir():
        return [
            ValidationIssue("missing-path", ".", "research route root is missing")
        ]

    for relative_path in REQUIRED_FILES:
        path = root / relative_path
        if path.is_symlink() or not path.is_file():
            issues.append(
                ValidationIssue(
                    "missing-path", relative_path, "required file is missing"
                )
            )
    for relative_path in REQUIRED_DIRECTORIES:
        path = root / relative_path
        if path.is_symlink() or not path.is_dir():
            issues.append(
                ValidationIssue(
                    "missing-path", relative_path, "required directory is missing"
                )
            )

    route_path = root / "ROUTE.md"
    if route_path.is_file() and not route_path.is_symlink():
        try:
            route_metadata, _ = parse_frontmatter(route_path)
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
    dependencies_by_id: dict[str, list[str]] = {}
    work_items = root / "work-items"
    if work_items.is_dir() and not work_items.is_symlink():
        for path in sorted(work_items.glob("*.md")):
            relative_path = _relative_path(root, path)
            if path.is_symlink() or not path.is_file():
                continue
            try:
                metadata, _ = parse_frontmatter(path)
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
            item_id = metadata.get("id")
            if not isinstance(item_id, str) or not ITEM_ID.fullmatch(item_id):
                continue
            items_by_id.setdefault(item_id, []).append(path)
            if not path.name.startswith(f"{item_id}-"):
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

    claims = root / ".research-route" / "claims"
    if claims.is_dir() and not claims.is_symlink():
        for path in sorted(claims.glob("*.lock")):
            relative_path = _relative_path(root, path)
            filename_id = path.stem
            try:
                claim = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                issues.append(
                    ValidationIssue("invalid-claim", relative_path, str(error))
                )
                continue
            claim_errors = _claim_record_errors(claim)
            for message in claim_errors:
                issues.append(ValidationIssue("invalid-claim", relative_path, message))
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
    _validate_markdown_links(root, issues)
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


def scaffold_handoff(root: Path) -> Path:
    route = _require_route(root)
    metadata, route_body = parse_frontmatter(route)
    handoff = root / "HANDOFF.md"
    if handoff.is_symlink() or not handoff.is_file():
        raise ValueError(f"missing HANDOFF.md in {root}")
    original = handoff.read_bytes()
    if original.count(HANDOFF_BEGIN) != 1 or original.count(HANDOFF_END) != 1:
        raise ValueError("HANDOFF.md must contain exactly one mechanical marker pair")
    prefix, remainder = original.split(HANDOFF_BEGIN, 1)
    _, suffix = remainder.split(HANDOFF_END, 1)

    items: list[dict[str, object]] = []
    items_by_id: dict[str, list[Path]] = {}
    work_items = _require_directory(root / "work-items")
    for path in sorted(work_items.glob("*.md")):
        if path.is_symlink():
            raise ValueError(f"symlinked work item is not allowed: {path}")
        if not path.is_file():
            continue
        item_metadata, _ = parse_frontmatter(path)
        record_errors = _work_item_record_errors(item_metadata)
        if record_errors:
            raise ValueError(f"invalid work item {path}: {record_errors[0][1]}")
        items.append(item_metadata)
        item_id = item_metadata["id"]
        assert isinstance(item_id, str)
        items_by_id.setdefault(item_id, []).append(path)

    duplicate_issues = _duplicate_item_issues(root, items_by_id)
    if duplicate_issues:
        raise ValueError(f"ambiguous work items: {duplicate_issues[0].message}")
    known_ids = set(items_by_id)
    active_claims: list[str] = []
    claimed_next_actions: list[str] = []
    claimed_ids: set[object] = set()
    claims = root / ".research-route" / "claims"
    if claims.is_symlink() or claims.exists():
        _require_directory(claims)
        for path in sorted(claims.glob("*.lock")):
            if path.is_symlink():
                raise ValueError(f"symlinked claim is not allowed: {path}")
            claim = json.loads(path.read_text(encoding="utf-8"))
            claim_errors = _claim_record_errors(claim)
            if claim_errors:
                raise ValueError(f"invalid claim {path}: {claim_errors[0]}")
            assert isinstance(claim, dict)
            identity_errors = _claim_identity_errors(claim, path.stem)
            if identity_errors:
                raise ValueError(f"invalid claim {path}: {identity_errors[0][1]}")
            reference_errors = _claim_reference_errors(claim, path.stem, known_ids)
            if reference_errors:
                raise ValueError(f"invalid claim {path}: {reference_errors[0][1]}")
            claimed_ids.add(claim.get("item_id"))
            active_claims.append(
                f"- {claim.get('item_id')}: {claim.get('owner')}"
            )
            item = next(item for item in items if item.get("id") == claim.get("item_id"))
            claimed_next_actions.append(
                f"- Continue {claim.get('item_id')}: {item.get('title')} "
                f"(owner: {claim.get('owner')})"
            )

    statuses = {item.get("id"): item.get("status") for item in items}
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
        route.stat().st_mtime, timezone.utc
    ).isoformat()
    blocks_match = re.search(
        r"(?ms)^## Blocks[ \t]*\r?\n(.*?)(?=^## |\Z)", route_body
    )
    blocks = blocks_match.group(1).strip() if blocks_match else ""
    next_action = (
        claimed_next_actions[0]
        if claimed_next_actions
        else (
            open_items[0].replace("- ", "- Start ", 1)
            if open_items
            else "- Ask the researcher to define the next work item."
        )
    )
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
    _atomic_write_bytes(
        handoff, prefix + HANDOFF_BEGIN + mechanical + HANDOFF_END + suffix
    )
    return handoff


def migrate_route(root: Path, target_version: int, apply: bool) -> MigrationPlan:
    route = _require_route(root)
    metadata, _ = parse_frontmatter(route)
    current_version = metadata.get("schema_version")
    if type(current_version) is not int:
        raise ValueError("ROUTE.md schema_version must be an integer")
    if current_version > PROJECT_SCHEMA_VERSION:
        return MigrationPlan(
            current_version,
            target_version,
            (f"unsupported current schema version {current_version}",),
            False,
        )
    if target_version == current_version:
        return MigrationPlan(current_version, target_version, (), True)
    migration = MIGRATIONS.get((current_version, target_version))
    if migration is None:
        return MigrationPlan(
            current_version,
            target_version,
            (f"no migration from schema version {current_version} to {target_version}",),
            False,
        )
    return MigrationPlan(
        current_version,
        target_version,
        migration(root, apply),
        True,
    )


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
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--root", type=Path, required=True)
    validate_parser.add_argument("--json", action="store_true")
    handoff_parser = commands.add_parser("handoff")
    handoff_parser.add_argument("--root", type=Path, required=True)
    migrate_parser = commands.add_parser("migrate")
    migrate_parser.add_argument("--root", type=Path, required=True)
    migrate_parser.add_argument("--to", type=int, required=True, dest="target_version")
    migrate_parser.add_argument("--apply", action="store_true")
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
        elif arguments.command == "validate":
            issues = validate_route(arguments.root)
            if arguments.json:
                print(json.dumps([asdict(issue) for issue in issues], ensure_ascii=False))
            else:
                for issue in issues:
                    print(f"{issue.path}: {issue.code}: {issue.message}")
            return 1 if issues else 0
        elif arguments.command == "handoff":
            scaffold_handoff(arguments.root)
        elif arguments.command == "migrate":
            plan = migrate_route(
                arguments.root, arguments.target_version, arguments.apply
            )
            if arguments.apply and not plan.applicable:
                print("error: refusing to apply unknown migration", file=sys.stderr)
            if plan.current_version == plan.target_version:
                print(f"already at schema version {plan.current_version}")
            else:
                if plan.applicable and not arguments.apply:
                    print("dry run; no files modified")
                for change in plan.changes:
                    print(change)
            return 0 if plan.applicable else 1
    except (FileExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
