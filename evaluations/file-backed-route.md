# File-backed route smoke record

## Run

An external temporary project root was initialized, given one `rr-001` work item, claimed, and supplied a real Markdown output. `complete` persisted `status: closed`, the completing owner, and the normalized output path, then removed the active claim. Canonical `ROUTE.md` was updated with a destination and exact next action; `HANDOFF.md` was generated and its five intellectual sections were declared. `validate --checkpoint handoff` returned zero issues.

## Cold restart

A fresh context receiving only the project root can identify the destination, completed output, schema state, absence of blocks, and exact next action from `ROUTE.md`, `HANDOFF.md`, and linked artifacts. The executable test covers the file-backed sequence and handoff checkpoint; fresh-agent interpretation remains a manual evaluation protocol. No private profile text is copied into the handoff or diagnostics.

## Provenance

The run is exercised by `tests/test_route_v2.py::RouteV2Tests::test_file_backed_route_replay_validates_handoff`; no external service, network dependency, or scholarly-quality claim is involved.
