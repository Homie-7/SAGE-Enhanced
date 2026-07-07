"""VAL adapter + operator status: the operational path for the managed
service. VAL HTTP behaviour is tested against a fake gateway (mocked
transport shape only — no real VAL facts are assumed)."""

from __future__ import annotations

import importlib
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.providers.base import ProviderCapabilities
from app.providers.val import VALProvider
from app.schemas.tasks import TaskSpec


def caps(**endpoint) -> ProviderCapabilities:
    return ProviderCapabilities.model_validate({
        "provider": "val", "model": "val-large",
        "endpoint": {"base_url": "https://val.internal/v1",
                     "api_style": "openai_chat",
                     "auth_env": "VAL_API_KEY",
                     "transport_retries": 0, **endpoint},
    })


def spec() -> TaskSpec:
    return TaskSpec(task_name="source_audit", system_prompt="sys",
                    user_prompt="user", output_schema={})


def patch_transport(monkeypatch, handler):
    """Route the adapter's httpx client through a MockTransport."""
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)


# --- readiness ---------------------------------------------------------------

def test_readiness_reports_every_missing_fact(monkeypatch):
    monkeypatch.delenv("VAL_API_KEY", raising=False)
    unwired = ProviderCapabilities.model_validate({"provider": "val"})
    ready, detail = VALProvider(unwired).readiness()
    assert not ready
    for needle in ("base_url", "api_style", "model", "VAL_API_KEY"):
        assert needle in detail


def test_readiness_ok_when_wired(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")
    ready, detail = VALProvider(caps()).readiness()
    assert ready and "openai_chat" in detail


# --- run_task ----------------------------------------------------------------

async def test_unwired_val_fails_with_managed_service_message(monkeypatch):
    monkeypatch.delenv("VAL_API_KEY", raising=False)
    unwired = ProviderCapabilities.model_validate({"provider": "val"})
    result = await VALProvider(unwired).run_task(spec())
    assert not result.valid
    assert "SAGE administrator" in result.error
    assert "users never supply API keys" in result.error


async def test_openai_chat_happy_path(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        })

    patch_transport(monkeypatch, handler)
    result = await VALProvider(caps()).run_task(spec())
    assert result.valid and result.parsed == {"ok": True}
    assert seen["url"] == "https://val.internal/v1/chat/completions"
    assert seen["auth"] == "Bearer temp-key"
    assert seen["body"]["model"] == "val-large"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert result.usage.input_tokens == 12 and result.usage.output_tokens == 3


async def test_anthropic_messages_style(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/messages")
        body = json.loads(request.content)
        assert body["system"] == "sys"
        return httpx.Response(200, json={
            "content": [{"type": "text", "text": '{"ok": 1}'}],
            "usage": {"input_tokens": 5, "output_tokens": 2},
        })

    patch_transport(monkeypatch, handler)
    result = await VALProvider(caps(api_style="anthropic_messages")).run_task(spec())
    assert result.valid and result.parsed == {"ok": 1}
    assert result.usage.input_tokens == 5


async def test_credential_rejection_is_admin_facing(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "expired-temp-key")
    patch_transport(monkeypatch, lambda r: httpx.Response(401, json={"error": "bad key"}))
    result = await VALProvider(caps()).run_task(spec())
    assert not result.valid
    assert "401" in result.error and "SAGE administrator" in result.error


async def test_transport_retry_then_explicit_failure(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ConnectError("gateway unreachable")

    patch_transport(monkeypatch, handler)
    monkeypatch.setattr("asyncio.sleep", _instant_sleep)
    result = await VALProvider(caps(transport_retries=1)).run_task(spec())
    assert attempts["n"] == 2  # one retry on transport errors, then stop
    assert not result.valid and "2 attempt(s)" in result.error


async def _instant_sleep(_): return None


async def test_prose_wrapped_json_still_yields_parsed(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")
    patch_transport(monkeypatch, lambda r: httpx.Response(200, json={
        "choices": [{"message": {"content":
            'Here is the result:\n```json\n{"a": 1}\n```'}}]}))
    result = await VALProvider(caps()).run_task(spec())
    assert result.valid and result.parsed == {"a": 1}


async def test_non_json_text_fails_for_repair_round(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")
    patch_transport(monkeypatch, lambda r: httpx.Response(200, json={
        "choices": [{"message": {"content": "I cannot answer in JSON."}}]}))
    result = await VALProvider(caps()).run_task(spec())
    assert not result.valid and "not a single JSON object" in result.error


async def test_non_retry_on_http_error_status(monkeypatch):
    monkeypatch.setenv("VAL_API_KEY", "temp-key")
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(500, text="gateway exploded")

    patch_transport(monkeypatch, handler)
    result = await VALProvider(caps(transport_retries=2)).run_task(spec())
    assert attempts["n"] == 1  # HTTP error statuses are reported, not retried
    assert not result.valid and "500" in result.error


# --- operator status endpoint ------------------------------------------------

def make_client(tmp_path, monkeypatch, *, admin: bool):
    monkeypatch.setenv("SAGE_DB_PATH", str(tmp_path / "sage.db"))
    monkeypatch.setenv("SAGE_ARTEFACT_ROOT", str(tmp_path / "artefacts"))
    monkeypatch.setenv("SAGE_PROVIDER", "val")
    monkeypatch.setenv("SAGE_ADMIN_MODE", "1" if admin else "0")
    import app.config, app.api.deps, app.main
    importlib.reload(app.config)
    importlib.reload(app.api.deps)
    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_admin_status_hidden_in_standard_mode(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, admin=False)
    assert client.get("/api/admin/status").status_code == 403


def test_admin_status_reports_unwired_val_honestly(tmp_path, monkeypatch):
    monkeypatch.delenv("VAL_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = make_client(tmp_path, monkeypatch, admin=True)
    body = client.get("/api/admin/status").json()
    assert body["ok"] is False  # default provider (val) not ready
    assert body["default_provider"] == "val"
    assert body["providers"]["val"]["ready"] is False
    assert "base_url" in body["providers"]["val"]["detail"]
    assert body["providers"]["mock"]["ready"] is True
    assert body["providers"]["claude"]["ready"] is False
    assert body["database"]["writable"] is True
    assert body["canonical_prompts"]["present"] is True
