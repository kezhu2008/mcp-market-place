"""Bedrock AgentCore harness invocation.

Used by the backend `/test-function` endpoint. The webhook lambda has its
own copy of this routine inside `webhook/handler.py` to keep its zip artifact
self-contained (no shared package between the two lambdas).
"""

from __future__ import annotations

import hashlib
import json
import time

import boto3


class HarnessError(Exception):
    pass


def _session_id(session_key: str) -> str:
    # AgentCore requires runtimeSessionId length >= 33; pad with a hex digest.
    pad = hashlib.sha256(session_key.encode()).hexdigest()
    return (session_key + "-" + pad)[:64]


def invoke_harness(
    fn: dict,
    text: str,
    session_key: str,
    region: str,
    gateways: list[dict] | None = None,
) -> tuple[str, int, str]:
    """Invoke an AgentCore runtime synchronously.

    Returns (output, latencyMs, raw_body).

    ``gateways`` is a list of ``{id, url}`` records appended to the payload
    so the harness can connect to the listed AgentCore gateways as MCP
    servers. The harness implementation is responsible for honoring this
    contract.
    """
    if fn.get("type") != "bedrock_harness":
        raise HarnessError(f"unsupported function type: {fn.get('type')!r}")

    client = boto3.client("bedrock-agentcore", region_name=region)
    prompt_template = fn.get("promptTemplate") or "{text}"
    try:
        prompt = prompt_template.format(text=text)
    except (KeyError, IndexError) as e:
        raise HarnessError(f"promptTemplate format error: {e}") from e

    payload: dict = {"prompt": prompt}
    if gateways:
        payload["gateways"] = gateways

    kwargs: dict = {
        "agentRuntimeArn": fn["agentRuntimeArn"],
        "runtimeSessionId": _session_id(session_key),
        "payload": json.dumps(payload).encode(),
        "contentType": "application/json",
        "accept": "application/json",
    }
    qualifier = fn.get("qualifier")
    if qualifier:
        kwargs["qualifier"] = qualifier

    t0 = time.time()
    resp = client.invoke_agent_runtime(**kwargs)
    body = resp["response"].read().decode()
    latency_ms = int((time.time() - t0) * 1000)

    # AgentCore harness payloads are application-defined. By convention we
    # surface `output`/`message` if present; otherwise fall back to raw text.
    out = body
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            out = parsed.get("output") or parsed.get("message") or body
        elif isinstance(parsed, str):
            out = parsed
    except json.JSONDecodeError:
        pass

    return out[:4096], latency_ms, body
