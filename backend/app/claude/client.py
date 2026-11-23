from __future__ import annotations

import anthropic

from app.core.config import CLAUDE_MODEL

_client: anthropic.AsyncAnthropic | None = None


def client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


class ClaudeError(RuntimeError):
    pass


def _request_kwargs() -> dict:
    return {
        "model": CLAUDE_MODEL,
        "max_tokens": 16000,
        "output_config": {"effort": "medium"},
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
    }


async def call_structured(system: str, content, model_cls):
    try:
        response = await client().beta.messages.parse(
            **_request_kwargs(),
            system=system,
            output_format=model_cls,
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.CredentialsError as e:
        raise ClaudeError(
            f"Claude credentials could not be loaded ({e}). If you use `ant auth login`, run it again."
        ) from e
    except anthropic.AuthenticationError as e:
        raise ClaudeError(
            "Claude rejected the credentials. Check the API key, or run `ant auth login` again if you signed in."
        ) from e
    except anthropic.RateLimitError as e:
        raise ClaudeError("Claude rate limit reached; try again shortly.") from e
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e.message).lower():
            raise ClaudeError(
                "The Anthropic account has no API credits left. Add credits under Billing in the Claude Console, then retry."
            ) from e
        raise ClaudeError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ClaudeError("Could not reach the Claude API.") from e
    return _parsed(response, model_cls)


def _parsed(response, model_cls):
    if response.stop_reason == "refusal":
        raise ClaudeError("Claude declined to process this document.")
    if response.stop_reason == "max_tokens":
        raise ClaudeError("Claude's answer was cut off (document too long).")
    parsed = response.parsed_output
    if parsed is None:
        raise ClaudeError("Claude returned no structured output.")
    return parsed if isinstance(parsed, model_cls) else model_cls.model_validate(parsed)
