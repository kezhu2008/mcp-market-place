"""Platform default AgentCore harness.

Reads MODEL_ID and SYSTEM_PROMPT from env at startup; on each invoke,
extracts ``prompt`` from the payload and calls Bedrock ``converse`` with
the configured model + system prompt. Returns ``{"output": <text>}``.

v1 ignores ``payload.gateways`` — MCP gateway tool wiring is a follow-up.
The platform passes them in for forward compatibility; the container just
doesn't connect to them yet.
"""

from __future__ import annotations

import os
from typing import Any

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Set at container start by AgentCore's environmentVariables (see
# backend/app/services/agentcore_harness.py:create). Defaults make local
# dev runs do something sensible if the env vars aren't injected.
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", "You are a helpful assistant.")

AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")

app = BedrockAgentCoreApp()
_bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = (payload or {}).get("prompt") or ""
    if not prompt:
        return {"output": ""}

    kwargs: dict[str, Any] = {
        "modelId": MODEL_ID,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
    }
    if SYSTEM_PROMPT:
        kwargs["system"] = [{"text": SYSTEM_PROMPT}]

    resp = _bedrock.converse(**kwargs)
    blocks = resp["output"]["message"]["content"]
    text = "".join(b.get("text", "") for b in blocks)
    return {"output": text}


if __name__ == "__main__":
    app.run()
