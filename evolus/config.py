"""Settings from the environment (or an untracked .env). Secret values are never printed, logged or stored:
every text that leaves this package for a log or a results file goes through ``redact``."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from twohands import REPO

SECRET_NAMES = ("EVOLUS_KEY", "EVOLUS_USER_KEY", "AMD_KEY", "TWOHANDS_GATE_TOKEN", "EVOLUS_CALLBACK_KEY")
IDS_FILE = Path(__file__).resolve().parent / "ids.json"   # ids made by `python -m evolus setup` (not secrets)
API = "https://api.evolus.ai"
DEFAULT_WORKSPACE = "https://app.evolus.ai"


def _dotenv() -> dict:
    out: dict = {}
    for envf in (REPO / ".env", REPO.parent / ".env"):
        if not envf.is_file():
            continue
        for line in envf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


def _get(name: str, files: dict) -> str:
    return (os.environ.get(name) or files.get(name) or "").strip()


@dataclass
class Settings:
    key: str = field(default="", repr=False)
    app_id: str = ""
    extractor_agent_id: str = ""
    extractor_id: str = ""
    library_id: str = ""
    workflow_id: str = ""
    filing_workflow_id: str = ""
    audit_workflow_id: str = ""
    agent: str = ""                      # "applicationId:agentId" as listed by GET /v1/models
    workspace_url: str = DEFAULT_WORKSPACE
    public_url: str = ""                 # where this app is reachable (crop links in the hand-off)
    gate_token: str = field(default="", repr=False)
    callback_key: str = field(default="", repr=False)
    api: str = API
    user_key: str = field(default="", repr=False)   # optional personal User API key (extractor schema, libraries)
    reviewer_email: str = ""

    @classmethod
    def load(cls) -> "Settings":
        f = _dotenv()
        ids = load_ids()
        env_g = lambda n: _get(n, f)  # noqa: E731
        idmap = {"EVOLUS_EXTRACTOR_AGENT_ID": "extractor_agent_id", "EVOLUS_EXTRACTOR_ID": "extractor_id",
                 "EVOLUS_LIBRARY_ID": "library_id", "EVOLUS_WORKFLOW_ID": "workflow_id", "EVOLUS_AGENT": "agent",
                 "EVOLUS_FILING_WORKFLOW_ID": "filing_workflow_id", "EVOLUS_AUDIT_WORKFLOW_ID": "audit_workflow_id"}
        g = lambda n: str(ids.get(idmap[n]) or "") or env_g(n) if n in idmap else env_g(n)  # noqa: E731
        return cls(key=g("EVOLUS_KEY"), app_id=g("EVOLUS_APP_ID"), extractor_agent_id=g("EVOLUS_EXTRACTOR_AGENT_ID"),
                   extractor_id=g("EVOLUS_EXTRACTOR_ID"), library_id=g("EVOLUS_LIBRARY_ID"),
                   workflow_id=g("EVOLUS_WORKFLOW_ID"), filing_workflow_id=g("EVOLUS_FILING_WORKFLOW_ID"),
                   audit_workflow_id=g("EVOLUS_AUDIT_WORKFLOW_ID"), agent=g("EVOLUS_AGENT"),
                   workspace_url=(g("EVOLUS_WORKSPACE_URL") or DEFAULT_WORKSPACE).rstrip("/"),
                   public_url=g("TWOHANDS_PUBLIC_URL").rstrip("/"), gate_token=g("TWOHANDS_GATE_TOKEN"),
                   callback_key=g("EVOLUS_CALLBACK_KEY"), api=(g("EVOLUS_API") or API).rstrip("/"),
                   user_key=g("EVOLUS_USER_KEY"), reviewer_email=g("EVOLUS_REVIEWER_EMAIL"))

    def secrets(self) -> list[str]:
        vals = [self.key, self.gate_token, self.callback_key, self.user_key]
        f = _dotenv()
        vals += [os.environ.get(n, "") for n in SECRET_NAMES] + [f.get(n, "") for n in SECRET_NAMES]
        return sorted({v for v in vals if v and len(v) >= 6}, key=len, reverse=True)

    def configured(self) -> dict:
        """Which building blocks can run (booleans only; no values)."""
        rest = bool(self.key and self.app_id)
        return {"key": bool(self.key), "app_id": bool(self.app_id),
                "extractor": rest and bool(self.extractor_agent_id and self.extractor_id),
                "ai_tools": rest, "library": rest and bool(self.library_id),
                "workflow": rest and bool(self.workflow_id), "filing_workflow": rest and bool(self.filing_workflow_id),
                "audit_workflow": rest and bool(self.audit_workflow_id), "user_key": bool(self.user_key), "agent_chat": bool(self.key),
                "gate_token": bool(self.gate_token)}


def load_ids(path: Path | None = None) -> dict:
    try:
        return json.loads((path or IDS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_ids(ids: dict, path: Path | None = None) -> None:
    (path or IDS_FILE).write_text(json.dumps(ids, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8")


def redact(obj, secrets: list[str] | None = None):
    """Deep copy of obj with every secret value replaced by '***'."""
    secrets = Settings.load().secrets() if secrets is None else secrets
    if isinstance(obj, str):
        for s in secrets:
            obj = obj.replace(s, "***")
        return obj
    if isinstance(obj, dict):
        return {redact(k, secrets): redact(v, secrets) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(x, secrets) for x in obj]
    return obj
