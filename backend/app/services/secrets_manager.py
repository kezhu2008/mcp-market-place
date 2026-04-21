"""AWS Secrets Manager wrapper. Values never logged and never returned by APIs."""

from __future__ import annotations

import boto3

from ..config import settings


def _sm():
    return boto3.client("secretsmanager", region_name=settings.region)


def _name(tenant_id: str, secret_id: str) -> str:
    return f"{settings.secrets_prefix}/{tenant_id}/{secret_id}"


def create(tenant_id: str, secret_id: str, value: str) -> str:
    res = _sm().create_secret(
        Name=_name(tenant_id, secret_id),
        SecretString=value,
    )
    return res["ARN"]


def put(tenant_id: str, secret_id: str, value: str) -> None:
    _sm().put_secret_value(
        SecretId=_name(tenant_id, secret_id),
        SecretString=value,
    )


def get(tenant_id: str, secret_id: str) -> str:
    res = _sm().get_secret_value(SecretId=_name(tenant_id, secret_id))
    return res["SecretString"]


def delete(tenant_id: str, secret_id: str) -> None:
    _sm().delete_secret(
        SecretId=_name(tenant_id, secret_id),
        ForceDeleteWithoutRecovery=True,
    )
