from __future__ import annotations

import os


class MissingCredentials(RuntimeError):
    pass


CREDENTIALS_HELP = (
    "Claude credentials are required: this app reads every document with Claude and has no other reader. "
    "Sign in with `ant auth login` (stored under ~/.config/anthropic), or set ANTHROPIC_API_KEY "
    "in the environment or in backend/.env, then start the server again."
)


def credential_source() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "API key"
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "auth token"
    try:
        from anthropic.lib.credentials import CredentialsFile, default_credentials

        result = default_credentials()
    except Exception:  # noqa: BLE001 - a broken profile on disk means "no usable credentials"
        return None
    if result is None:
        return None
    provider = result.provider
    return f"signed-in profile '{provider.profile}'" if isinstance(provider, CredentialsFile) else "workload identity"


def require_credentials() -> str:
    source = credential_source()
    if source is None:
        raise MissingCredentials(CREDENTIALS_HELP)
    return source
