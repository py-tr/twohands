"""Thin Evolus REST client. Endpoints as published on https://evolus.ai/developers (see docs/EVOLUS.md).

Auth: REST uses X-ApiKey + X-Application-Id; agent chat (OpenAI-compatible) uses Authorization: Bearer.
Pacing: at most one request per PACE_S seconds from this process (the workspace allows 60/min).
Every call is recorded in ``self.calls`` (method, endpoint template, status, ms) - never headers or keys.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from evolus.config import Settings, redact

PACE_S = 1.2


class EvolusError(Exception):
    def __init__(self, status: Any, endpoint: str, detail: str):
        super().__init__(f"{endpoint}: HTTP {status}: {detail[:300]}")
        self.status, self.endpoint, self.detail = status, endpoint, detail[:300]


class NotConfigured(Exception):
    pass


class EvolusClient:
    def __init__(self, settings: Optional[Settings] = None, transport: Optional[httpx.BaseTransport] = None,
                 pace_s: float = PACE_S, timeout: float = 180.0):
        self.s = settings or Settings.load()
        self._secrets = self.s.secrets()
        self._http = httpx.Client(base_url=self.s.api, timeout=timeout, transport=transport)
        self.pace_s = pace_s
        self._last = 0.0
        self._lock = threading.Lock()
        self.calls: list[dict] = []

    # ------------------------------------------------------------------ plumbing
    def _rest_headers(self) -> dict:
        if not self.s.key or not self.s.app_id:
            raise NotConfigured("EVOLUS_KEY and EVOLUS_APP_ID are needed for the REST API")
        return {"X-ApiKey": self.s.key, "X-Application-Id": self.s.app_id, "Accept": "application/json"}

    def _user_headers(self) -> dict:
        if not self.s.user_key or not self.s.app_id:
            raise NotConfigured("EVOLUS_USER_KEY (a personal User API key) is needed for this call")
        return {"X-User-ApiKey": self.s.user_key, "X-Application-Id": self.s.app_id, "Accept": "application/json"}

    def rest(self, method: str, path: str, endpoint: str = "", body: Any = None, params: Optional[dict] = None,
             user: bool = False) -> Any:
        """Generic JSON call. user=True: the operation needs a personal User API key (per the spec)."""
        h = self._user_headers() if user else self._rest_headers()
        kw: dict = {"params": params} if params else {}
        if body is not None:
            h = h | {"Content-Type": "application/json"}
            kw["content"] = json.dumps(body, ensure_ascii=False).encode("utf-8")
        r = self._call(method, path, endpoint or f"{method} {path}", h, **kw)
        return self._json(r) if r.content else {}

    def _chat_headers(self) -> dict:
        if not self.s.key:
            raise NotConfigured("EVOLUS_KEY is needed for agent chat")
        return {"Authorization": "Bearer " + self.s.key, "Accept": "application/json"}

    def _call(self, method: str, path: str, endpoint: str, headers: dict, **kw) -> httpx.Response:
        with self._lock:
            wait = self._last + self.pace_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
        t0 = time.monotonic()
        try:
            r = self._http.request(method, path, headers=headers, **kw)
        except httpx.HTTPError as e:
            self.calls.append({"method": method, "endpoint": endpoint, "status": "error",
                               "ms": int((time.monotonic() - t0) * 1000)})
            raise EvolusError("network", endpoint, redact(f"{type(e).__name__}: {e}", self._secrets)) from None
        self.calls.append({"method": method, "endpoint": endpoint, "status": r.status_code,
                           "ms": int((time.monotonic() - t0) * 1000)})
        if r.status_code >= 400:
            hint = {402: " (workspace credits exhausted)", 409: " (workflow is switched off)",
                    401: " (key or application id rejected)", 429: " (rate limited)"}.get(r.status_code, "")
            raise EvolusError(r.status_code, endpoint, redact(r.text, self._secrets) + hint)
        return r

    @staticmethod
    def _json(r: httpx.Response) -> Any:
        try:
            return r.json()
        except ValueError:
            return {"text": r.text}

    # ------------------------------------------------------------------ agent chat (OpenAI-compatible)
    def models(self) -> list[dict]:
        r = self._call("GET", "/v1/models", "GET /v1/models", self._chat_headers())
        return (self._json(r) or {}).get("data") or []

    def chat(self, model: str, messages: list[dict], conversation_id: Optional[str] = None) -> dict:
        h = self._chat_headers() | {"Content-Type": "application/json"}
        if conversation_id:
            h["X-Conversation-Id"] = conversation_id
        r = self._call("POST", "/v1/chat/completions", "POST /v1/chat/completions", h,
                       content=json.dumps({"model": model, "messages": messages, "stream": False}))
        d = self._json(r) or {}
        text = ""
        try:
            text = d["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            pass
        return {"text": text, "conversation_id": r.headers.get("X-Conversation-Id"), "usage": d.get("usage"),
                "model": d.get("model")}

    # ------------------------------------------------------------------ document extractors
    def extract_file(self, agent_id: str, extractor_id: str, path: Path, output: str = "json") -> Any:
        ep = "POST /api/v1/agents/{agentId}/" + output + "/{extractorId}/ask-file"
        with open(path, "rb") as fh:
            r = self._call("POST", f"/api/v1/agents/{agent_id}/{output}/{extractor_id}/ask-file", ep,
                           self._rest_headers(), params={"useWebhook": "false"},
                           files={"file": (Path(path).name, fh, "image/jpeg")})
        d = self._json(r)
        if isinstance(d, dict):
            d.setdefault("_auditId", r.headers.get("X-AskFile-Audit-Id"))
            d.setdefault("_executionId", r.headers.get("X-AskFile-Execution-Id"))
        return d

    # ------------------------------------------------------------------ AI Tools
    def ai_tools(self) -> Any:
        return self._json(self._call("GET", "/api/v1/ai-tools", "GET /api/v1/ai-tools", self._rest_headers()))

    def run_tool(self, tool: str, text: str, secondary: Optional[str] = None, options: Optional[dict] = None) -> Any:
        body = {"text": text, "secondaryText": secondary, "options": options or {}}
        r = self._call("POST", f"/api/v1/ai-tools/{tool}/run", "POST /api/v1/ai-tools/{tool}/run",
                       self._rest_headers() | {"Content-Type": "application/json"}, content=json.dumps(body))
        return self._json(r)

    # ------------------------------------------------------------------ knowledge libraries
    def upload_document(self, library_id: str, filename: str, data: bytes, language: str = "en",
                        content_type: str = "text/plain") -> Any:
        r = self._call("POST", f"/api/v1/memories/{library_id}/documents",
                       "POST /api/v1/memories/{libraryId}/documents", self._rest_headers(),
                       params={"language": language}, files={"file": (filename, data, content_type)})
        return self._json(r)

    def list_documents(self, library_id: str) -> Any:
        return self._json(self._call("GET", f"/api/v1/memories/{library_id}/documents",
                                     "GET /api/v1/memories/{libraryId}/documents", self._rest_headers()))

    # ------------------------------------------------------------------ workflows
    def execute_workflow(self, workflow_id: str, input_text: str, parameters: Optional[dict] = None,
                         callback_url: Optional[str] = None, callback_key: Optional[str] = None) -> Any:
        """multipart/form-data (as documented): input, parameters, callbackUrl, callbackMethod, callbackApiKey..."""
        parts: list = [("input", (None, input_text.encode("utf-8"), "text/plain; charset=utf-8"))]
        if parameters:
            parts.append(("parameters", (None, json.dumps(parameters, ensure_ascii=False).encode("utf-8"))))
        if callback_url:
            parts += [("callbackUrl", (None, callback_url.encode())), ("callbackMethod", (None, b"POST"))]
            if callback_key:
                parts += [("callbackApiKey", (None, callback_key.encode())),
                          ("callbackApiKeyName", (None, b"X-Callback-Key"))]
        r = self._call("POST", f"/api/v1/workflows/{workflow_id}/execute",
                       "POST /api/v1/workflows/{workflowId}/execute", self._rest_headers(), files=parts)
        d = self._json(r) if r.content else {}
        d = d if isinstance(d, dict) else {"body": d}
        d.setdefault("executionId", r.headers.get("X-Workflow-Execution-Id"))
        return d

    def workflow_status(self, workflow_id: str, execution_id: str) -> Any:
        return self._json(self._call("GET", f"/api/v1/workflows/{workflow_id}/executions/{execution_id}",
                                     "GET /api/v1/workflows/{workflowId}/executions/{executionId}",
                                     self._rest_headers()))

    def close(self) -> None:
        self._http.close()
