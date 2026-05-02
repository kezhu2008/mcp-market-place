"""AWS Bedrock AgentCore Gateway provisioning.

Wraps three control-plane calls so a Gateway can be created from an OpenAPI
spec + an upstream API token:

    1. CreateApiKeyCredentialProvider — stores the token as a credential the
       gateway target can use to authenticate to the upstream API.
    2. CreateGateway — creates the MCP-protocol gateway.
    3. CreateGatewayTarget — wires the OpenAPI spec into the gateway and binds
       the credential provider to it.

Also exposes ``list_tools(gateway_url, region)`` which probes a deployed
gateway via a SigV4-signed JSON-RPC ``tools/list`` request — used by the
``POST /gateways/{id}/test`` endpoint so operators can validate a gateway
from the UI.

The exact field names for the AgentCore control plane are still firming up;
the tests stub this service out. If a real apply against AWS surfaces a
schema mismatch, adjust the kwargs here — none of the rest of the codebase
sees the AWS shape.
"""

from __future__ import annotations

import json
import time

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class GatewayProvisionError(Exception):
    pass


class GatewayInvocationError(Exception):
    pass


def _ctrl(region: str):
    return boto3.client("bedrock-agentcore-control", region_name=region)


def create(
    name: str,
    openapi_spec: str,
    token: str,
    region: str,
) -> dict:
    """Provision an AgentCore gateway from an OpenAPI spec + bearer token.

    Returns ``{gatewayArn, gatewayUrl, targetId, credentialProviderArn}``.
    """
    ctrl = _ctrl(region)
    cred_arn: str | None = None
    gateway_arn: str | None = None

    try:
        cp = ctrl.create_api_key_credential_provider(
            name=f"{name}_cred",
            apiKey=token,
        )
        cred_arn = cp.get("credentialProviderArn") or cp.get("arn")
        if not cred_arn:
            raise GatewayProvisionError("credentialProviderArn missing in response")

        gw = ctrl.create_gateway(
            name=name,
            protocolType="MCP",
            # Inbound auth: harness-side IAM. Operator can switch to JWT
            # later by editing the gateway out-of-band.
            authorizerType="AWS_IAM",
        )
        gateway_arn = gw.get("gatewayArn") or gw.get("arn")
        gateway_url = gw.get("gatewayUrl") or gw.get("url")
        if not gateway_arn or not gateway_url:
            raise GatewayProvisionError(f"create_gateway response missing arn/url: {gw!r}")

        tgt = ctrl.create_gateway_target(
            gatewayIdentifier=gateway_arn,
            name=f"{name}_target",
            targetConfiguration={
                "mcp": {
                    "openApiSchema": {"inlinePayload": openapi_spec},
                },
            },
            credentialProviderConfigurations=[
                {
                    "credentialProviderType": "API_KEY",
                    "credentialProvider": {
                        "apiKeyCredentialProvider": {"providerArn": cred_arn},
                    },
                },
            ],
        )
        target_id = tgt.get("targetId") or tgt.get("id")
        if not target_id:
            raise GatewayProvisionError(f"create_gateway_target response missing id: {tgt!r}")

        return {
            "gatewayArn": gateway_arn,
            "gatewayUrl": gateway_url,
            "targetId": target_id,
            "credentialProviderArn": cred_arn,
        }
    except Exception:
        # Best-effort cleanup on partial failure so we don't leak AWS resources.
        if gateway_arn:
            try:
                ctrl.delete_gateway(gatewayIdentifier=gateway_arn)
            except Exception:  # noqa: S110 — already failing, swallow
                pass
        if cred_arn:
            try:
                ctrl.delete_api_key_credential_provider(credentialProviderArn=cred_arn)
            except Exception:  # noqa: S110
                pass
        raise


def list_tools(gateway_url: str, region: str, timeout: float = 10.0) -> tuple[list[dict], int]:
    """Probe a deployed gateway with a SigV4-signed ``tools/list`` JSON-RPC.

    Returns ``([{name, description}, ...], latency_ms)``. Used by the test
    endpoint to confirm reachability, auth, and OpenAPI-to-MCP translation
    in one round-trip.

    Field shape on the response is best-effort against the AgentCore data
    plane; if real traffic surfaces a different envelope, update here.
    """
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    creds = boto3.Session().get_credentials()
    if creds is None:
        raise GatewayInvocationError("no AWS credentials available for SigV4")
    request = AWSRequest(
        method="POST",
        url=gateway_url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(creds, "bedrock-agentcore", region).add_auth(request)
    headers = dict(request.headers.items())

    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(gateway_url, content=body, headers=headers)
    except httpx.HTTPError as e:
        raise GatewayInvocationError(f"gateway unreachable: {e}") from e
    latency_ms = int((time.time() - t0) * 1000)

    if resp.status_code >= 400:
        raise GatewayInvocationError(f"gateway returned {resp.status_code}: {resp.text[:500]}")

    try:
        parsed = resp.json()
    except json.JSONDecodeError as e:
        raise GatewayInvocationError(f"non-JSON response: {resp.text[:500]}") from e

    # JSON-RPC envelope: {jsonrpc, id, result: {tools: [...]}}.
    result = parsed.get("result") if isinstance(parsed, dict) else None
    raw_tools = (result or {}).get("tools") if isinstance(result, dict) else None
    if not isinstance(raw_tools, list):
        raise GatewayInvocationError(f"unexpected response shape: {json.dumps(parsed)[:500]}")
    tools = [
        {"name": str(t.get("name", "")), "description": str(t.get("description", ""))}
        for t in raw_tools
        if isinstance(t, dict)
    ]
    return tools, latency_ms


def destroy(
    gateway_arn: str | None,
    target_id: str | None,
    credential_provider_arn: str | None,
    region: str,
) -> None:
    """Tear down a gateway and its credential provider. Idempotent-ish — logs
    are the operator's job; we swallow individual failures so a broken
    gateway can still be removed from our DB."""
    ctrl = _ctrl(region)
    if gateway_arn and target_id:
        try:
            ctrl.delete_gateway_target(gatewayIdentifier=gateway_arn, targetId=target_id)
        except Exception:  # noqa: S110
            pass
    if gateway_arn:
        try:
            ctrl.delete_gateway(gatewayIdentifier=gateway_arn)
        except Exception:  # noqa: S110
            pass
    if credential_provider_arn:
        try:
            ctrl.delete_api_key_credential_provider(credentialProviderArn=credential_provider_arn)
        except Exception:  # noqa: S110
            pass
