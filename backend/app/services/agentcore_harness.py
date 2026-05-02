"""AWS Bedrock AgentCore Runtime (a.k.a. Harness) provisioning.

A Harness is a deployed AgentCore runtime — a container that hosts the
agent code. The platform ships a default container image (overridable via
PLATFORM_HARNESS_IMAGE_URI). The image is contractually required to:

  - Read MODEL_ID and SYSTEM_PROMPT from environment variables at startup.
  - Accept an invoke payload of shape {prompt, gateways: [{id, url}]} on
    each request and connect to the listed gateways as MCP servers.

Field names on the AgentCore control plane are still firming up; tests
stub this service out. If a real apply against AWS surfaces a schema
mismatch, adjust the kwargs here — the rest of the codebase doesn't see
the AWS shape.
"""

from __future__ import annotations

import boto3


class HarnessProvisionError(Exception):
    pass


def _ctrl(region: str):
    return boto3.client("bedrock-agentcore-control", region_name=region)


def create(
    name: str,
    model: str,
    system_prompt: str,
    image_uri: str,
    role_arn: str,
    region: str,
) -> dict:
    """Provision an AgentCore runtime.

    Returns ``{agentRuntimeArn, agentRuntimeId, qualifier}``.
    """
    if not role_arn:
        raise HarnessProvisionError("PLATFORM_HARNESS_ROLE_ARN is not configured")
    if not image_uri:
        raise HarnessProvisionError("PLATFORM_HARNESS_IMAGE_URI is not configured")

    ctrl = _ctrl(region)
    runtime_arn: str | None = None
    try:
        resp = ctrl.create_agent_runtime(
            agentRuntimeName=name,
            agentRuntimeArtifact={
                "containerConfiguration": {"containerUri": image_uri},
            },
            roleArn=role_arn,
            # PUBLIC is the standard mode for runtimes that don't sit in a
            # customer VPC. Switch to VPC mode out-of-band if the harness
            # ever needs private network access.
            networkConfiguration={"networkMode": "PUBLIC"},
            environmentVariables={
                "MODEL_ID": model,
                "SYSTEM_PROMPT": system_prompt,
            },
        )
        runtime_arn = resp.get("agentRuntimeArn") or resp.get("arn")
        runtime_id = resp.get("agentRuntimeId") or resp.get("id")
        qualifier = resp.get("agentRuntimeVersion") or resp.get("version")
        if not runtime_arn or not runtime_id:
            raise HarnessProvisionError(f"create_agent_runtime response missing arn/id: {resp!r}")
        return {
            "agentRuntimeArn": runtime_arn,
            "agentRuntimeId": runtime_id,
            "qualifier": qualifier,
        }
    except Exception:
        # Best-effort cleanup if a partial state was created.
        if runtime_arn:
            try:
                ctrl.delete_agent_runtime(agentRuntimeArn=runtime_arn)
            except Exception:  # noqa: S110 — already failing, swallow
                pass
        raise


def destroy(agent_runtime_arn: str | None, region: str) -> None:
    """Tear down a runtime. Idempotent; swallows individual failures so a
    broken runtime can still be removed from our DB."""
    if not agent_runtime_arn:
        return
    ctrl = _ctrl(region)
    try:
        ctrl.delete_agent_runtime(agentRuntimeArn=agent_runtime_arn)
    except Exception:  # noqa: S110
        pass
