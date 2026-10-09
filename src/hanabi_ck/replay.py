"""Export recorded full games to a portable, dependency-free HTML viewer."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path


def export_replay(
    log_path: str | Path,
    output_path: str | Path,
    *,
    title: str = "Hanabi · Inside a cooperative decision",
) -> Path:
    source = Path(log_path).read_text(encoding="utf-8")
    records = []
    for number, line in enumerate(source.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on log line {number}") from exc
        if (
            not isinstance(record, dict)
            or record.get("event_kind", "turn") not in {"turn", "agent_error"}
            or not isinstance(record.get("observation"), dict)
        ):
            raise ValueError(f"Line {number} is not a full-game turn/error record")
        records.append(record)
    if not records:
        raise ValueError("Game log is empty")
    identities = {(r.get("experiment"), r.get("condition"), r.get("seed")) for r in records}
    if len(identities) != 1:
        raise ValueError("Export one game at a time; this log contains multiple games")
    # Script-safe JSON; model output and user text are never executable HTML.
    payload = json.dumps(
        {"title": title, "source_name": Path(log_path).name, "source": source}, ensure_ascii=False
    )
    payload = (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    template = files("hanabi_ck").joinpath("replay.html").read_text(encoding="utf-8")
    destination = Path(output_path)
    if destination.resolve() == Path(log_path).resolve():
        raise ValueError("HTML output must not overwrite the source log")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(template.replace("__REPLAY_DATA__", payload), encoding="utf-8")
    return destination.resolve()
