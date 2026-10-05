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


def _choice_fields(data: dict[str, Any]) -> dict[str, Any]:
    choice = data["choices"][0]
    message = choice["message"]
    content = message.get("content")
    reasoning_content = message.get("reasoning_content")
    reasoning = message.get("reasoning")
    selected = (
        content
        if isinstance(content, str) and content.strip()
        else reasoning_content
        if isinstance(reasoning_content, str) and reasoning_content.strip()
        else reasoning
        if isinstance(reasoning, str) and reasoning.strip()
        else ""
    )
    return {
        "finish_reason": choice.get("finish_reason"),
        "native_finish_reason": choice.get("native_finish_reason"),
        "content": content,
        "reasoning_content": reasoning_content,
        "reasoning": reasoning,
        "selected_text": selected,
    }


def _valid_basic_completion(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    fields = _choice_fields(data)
    selected = str(fields["selected_text"]).strip()
    ok = (
        fields["finish_reason"] != "length"
        and selected == "OK"
    )
    return ok, fields


def _valid_schema_completion(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    fields = _choice_fields(data)
    parsed: dict[str, Any] | None = None
    parse_error: str | None = None
    try:
        candidate = json.loads(str(fields["selected_text"]).strip())
        if isinstance(candidate, dict):
            parsed = candidate
        else:
            parse_error = "response JSON is not an object"
    except Exception as exc:
        parse_error = f"{type(exc).__name__}: {exc}"

    ok = (
        fields["finish_reason"] != "length"
        and parsed == {"ok": True}
    )
    fields["parsed_json"] = parsed
    fields["validation_error"] = parse_error
    return ok, fields


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
    openrouter_key = (
        os.getenv("OPENROUTER_API_KEY")
        if "openrouter.ai" in base_url
        else None
    )
    openai_key = os.getenv("OPENAI_API_KEY")
    api_key = explicit_key or openrouter_key or openai_key
    key_source = (
        "config"
        if explicit_key
        else "OPENROUTER_API_KEY"
        if openrouter_key
        else "OPENAI_API_KEY"
        if openai_key
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
            "No API key resolved. Set OPENROUTER_API_KEY or OPENAI_API_KEY before testing the remote endpoint."
        )
        return report

    headers = {"Authorization": f"Bearer {api_key}"}
    timeout_s = float(spec.get("timeout_s", 60.0))
    configured_max_tokens = int(spec.get("max_tokens", 256))
    configured_temperature = spec.get("temperature", 0.0)
    configured_structured_output = bool(spec.get("structured_output", False))
    extra_body = dict(spec.get("extra_body") or {})

    def apply_configured_controls(payload: dict[str, Any]) -> dict[str, Any]:
        out = dict(payload)
        out["max_tokens"] = configured_max_tokens
        if configured_temperature is not None:
            out["temperature"] = float(configured_temperature)
        reserved = set(out)
        collisions = reserved.intersection(extra_body)
        if collisions:
            raise ValueError(
                "agent.extra_body cannot override core payload fields: "
                + ", ".join(sorted(collisions))
            )
        out.update(extra_body)
        return out

    report["configured_controls"] = {
        "temperature": configured_temperature,
        "max_tokens": configured_max_tokens,
        "structured_output": configured_structured_output,
        "extra_body": extra_body,
    }

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
        basic_payload = apply_configured_controls(
            {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": 'Return exactly the word OK.',
                    }
                ],
            }
        )
        try:
            response = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=basic_payload,
            )
            http_ok = response.is_success
            basic_ok = False
            basic_entry: dict[str, Any] = {
                "status_code": response.status_code,
                "http_ok": http_ok,
                "ok": False,
                "body": _short_body(response),
            }
            if http_ok:
                try:
                    data = response.json()
                    basic_ok, fields = _valid_basic_completion(data)
                    basic_entry.update(fields)
                    basic_entry["returned_model"] = data.get("model")
                    basic_entry["provider"] = data.get("provider")
                    basic_entry["ok"] = basic_ok
                    if not basic_ok:
                        basic_entry["validation_warning"] = (
                            "HTTP succeeded but the model did not produce the "
                            "requested final answer before the token limit."
                        )
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

        # Stage 3: test strict structured output only when the experiment
        # actually requests it. Some OpenRouter routes support the model but
        # not json_schema response_format.
        if configured_structured_output:
            schema_payload = apply_configured_controls(
                {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": 'Return JSON with field "ok" set to true.',
                        }
                    ],
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
            )
            try:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=schema_payload,
                )
                http_ok = response.is_success
                schema_ok = False
                schema_entry: dict[str, Any] = {
                    "status_code": response.status_code,
                    "http_ok": http_ok,
                    "ok": False,
                    "body": _short_body(response),
                }
                if http_ok:
                    try:
                        data = response.json()
                        schema_ok, fields = _valid_schema_completion(data)
                        schema_entry.update(fields)
                        schema_entry["returned_model"] = data.get("model")
                        schema_entry["provider"] = data.get("provider")
                        schema_entry["ok"] = schema_ok
                        if not schema_ok:
                            schema_entry["validation_warning"] = (
                                "HTTP succeeded but no complete valid structured "
                                "answer was produced."
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
        else:
            schema_ok = True
            report["checks"]["structured_output"] = {
                "ok": True,
                "skipped": True,
                "reason": (
                    "structured_output is disabled in this config; Hanabi will "
                    "request JSON in the prompt and validate it client-side."
                ),
            }

    report["ok"] = bool(basic_ok and schema_ok)
    if basic_ok and not schema_ok:
        report["recommendation"] = (
            "Basic chat produced a usable answer, but the structured-output "
            "check did not. Inspect finish_reason/content first; if the model "
            "completed normally but rejected the schema, disable structured_output."
        )
    elif not basic_ok:
        report["recommendation"] = (
            "Basic chat did not yield a usable final answer. Check the HTTP "
            "status, finish_reason, and whether reasoning consumed the token "
            "budget before final content was emitted."
        )
    else:
        report["recommendation"] = (
            "The configured request mode is usable. "
            + (
                "Basic chat and strict structured output both work."
                if configured_structured_output
                else "Basic chat works; structured output is disabled and "
                "responses will be JSON-validated client-side."
            )
        )
    return report


def format_api_check(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)
