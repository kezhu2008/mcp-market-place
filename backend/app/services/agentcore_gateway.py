"""AWS Bedrock AgentCore Gateway provisioning.

Wraps three control-plane calls so a Gateway can be created from an OpenAPI
spec + an upstream API token:

    1. CreateApiKeyCredentialProvider — stores the token as a credential the
       gateway target can use to authenticate to the upstream API.
    2. CreateGateway — creates the MCP-protocol gateway.
    3. CreateGatewayTarget — wires the OpenAPI spec into the gateway and binds
       the credential provider to it.

The exact field names for the AgentCore control plane are still firming up;
the tests stub this service out. If a real apply against AWS surfaces a
schema mismatch, adjust the kwargs here — none of the rest of the codebase
sees the AWS shape.
"""

from __future__ import annotations

import boto3


class GatewayProvisionError(Exception):
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
            name=f"{name}-cred",
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
            raise GatewayProvisionError(
                f"create_gateway response missing arn/url: {gw!r}"
            )

        tgt = ctrl.create_gateway_target(
            gatewayIdentifier=gateway_arn,
            name=f"{name}-target",
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
