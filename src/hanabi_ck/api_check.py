from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from .runner import load_config


def _short_body(response: httpx.Response, limit: int = 1200) -> str:
    text = response.text.strip()
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def _agent_spec_from_config(cfg: dict[str, Any]) -> dict[str, Any]:
    spec = cfg.get("agent")
    if isinstance(spec, dict):
        return dict(spec)

    agents = cfg.get("agents")
    if isinstance(agents, list) and agents and isinstance(agents[0], dict):
        return dict(agents[0])

    raise ValueError("Config must contain an 'agent' mapping or non-empty 'agents' list")


def check_openai_compatible_api(config_path: str | Path) -> dict[str, Any]:
    cfg = load_config(config_path)
    spec = _agent_spec_from_config(cfg)
    if spec.get("type") != "openai_compatible":
        raise ValueError("api-check requires an openai_compatible agent")

    base_url = str(
        spec.get("base_url")
        or os.getenv("OPENAI_BASE_URL")
        or "http://localhost:1234/v1"
    ).rstrip("/")
    model = str(spec["model"])

    explicit_key = spec.get("api_key")
    env_key = os.getenv("OPENAI_API_KEY")
    api_key = explicit_key or env_key
    key_source = (
        "config"
        if explicit_key
        else "OPENAI_API_KEY"
        if env_key
        else "missing"
    )

    report: dict[str, Any] = {
        "config": str(config_path),
        "base_url": base_url,
        "model": model,
        "api_key_present": bool(api_key),
        "api_key_source": key_source,
        "checks": {},
    }

    if not api_key:
        report["ok"] = False
        report["error"] = (
            "No API key resolved. Set OPENAI_API_KEY before testing the remote endpoint."
        )
        return report

    headers = {"Authorization": f"Bearer {api_key}"}
    timeout_s = float(spec.get("timeout_s", 60.0))

    with httpx.Client(timeout=timeout_s) as client:
        # Stage 1: endpoint/auth discovery. Some providers may not expose /models,
        # so failure here is recorded but does not stop the basic chat test.
        try:
            response = client.get(f"{base_url}/models", headers=headers)
            report["checks"]["models"] = {
                "status_code": response.status_code,
                "ok": response.is_success,
                "body": _short_body(response),
            }
        except Exception as exc:
            report["checks"]["models"] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        # Stage 2: minimal chat completion, intentionally without response_format.
        basic_payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": 'Return exactly the word OK.',
                }
            ],
            "temperature": 0.0,
            "max_tokens": 16,
        }
        try:
            response = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=basic_payload,
            )
            basic_ok = response.is_success
            basic_entry: dict[str, Any] = {
                "status_code": response.status_code,
                "ok": basic_ok,
                "body": _short_body(response),
            }
            if basic_ok:
                try:
                    data = response.json()
                    message = data["choices"][0]["message"]
                    basic_entry["content"] = message.get("content")
                    basic_entry["reasoning_content"] = message.get(
                        "reasoning_content"
                    )
                    basic_entry["returned_model"] = data.get("model")
                except Exception as exc:
                    basic_entry["parse_warning"] = (
                        f"{type(exc).__name__}: {exc}"
                    )
            report["checks"]["basic_chat"] = basic_entry
        except Exception as exc:
            report["checks"]["basic_chat"] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            basic_ok = False

        # Stage 3: test the exact structured-output capability used by Hanabi.
        schema_payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": 'Return JSON with field "ok" set to true.',
                }
            ],
            "temperature": 0.0,
            "max_tokens": 32,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "hanabi_connectivity_check",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "ok": {"type": "boolean", "const": True}
                        },
                        "required": ["ok"],
                        "additionalProperties": False,
                    },
                },
            },
        }
        try:
            response = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=schema_payload,
            )
            schema_ok = response.is_success
            schema_entry: dict[str, Any] = {
                "status_code": response.status_code,
                "ok": schema_ok,
                "body": _short_body(response),
            }
            if schema_ok:
                try:
                    data = response.json()
                    message = data["choices"][0]["message"]
                    schema_entry["content"] = message.get("content")
                    schema_entry["reasoning_content"] = message.get(
                        "reasoning_content"
                    )
                except Exception as exc:
                    schema_entry["parse_warning"] = (
                        f"{type(exc).__name__}: {exc}"
                    )
            report["checks"]["structured_output"] = schema_entry
        except Exception as exc:
            report["checks"]["structured_output"] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            schema_ok = False

    report["ok"] = bool(basic_ok and schema_ok)
    if basic_ok and not schema_ok:
        report["recommendation"] = (
            "Connectivity and model access work, but strict json_schema failed. "
            "Set structured_output: false for this provider/model."
        )
    elif not basic_ok:
        report["recommendation"] = (
            "Basic chat failed. Check API key, model identifier, endpoint access, "
            "and the returned HTTP status/body."
        )
    else:
        report["recommendation"] = (
            "Basic chat and strict structured output both work. "
            "The Hanabi experiment can use structured_output: true."
        )
    return report


def format_api_check(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)
