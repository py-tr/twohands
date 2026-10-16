"""OpenTimestamps for audit reports: anchor a report's Merkle root in time.

What is stamped is a small file holding the root (``<root>\\n``, the CLI's merkle_root.txt; for the sample audit,
results/sample_audit_root.txt), exactly as ``ots stamp <file>`` would: SHA-256 of the file, a 16-byte random nonce
appended and hashed again (so the calendars never see the file's own hash), and that digest POSTed to public
calendar servers. Each calendar answers with a commitment path to a pending attestation; it later aggregates the
digest into a Bitcoin transaction (a few hours), after which ``ots upgrade <file>.ots`` fetches the Bitcoin
attestation and ``ots verify <file>.ots`` checks it against the chain. Only a hash leaves the machine.

The proof file is the standard detached ``.ots`` format, so the reference client (``pip install
opentimestamps-client``) reads, upgrades and verifies it. This module is standard library only, because the
reference client imports python-bitcoinlib, which loads OpenSSL through ctypes and does not start on every platform
(it fails on Windows); stamping only needs the calendar HTTP API.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# The reference client's default calendars (otsclient: --calendar default list).
CALENDARS = ("https://a.pool.opentimestamps.org", "https://b.pool.opentimestamps.org",
             "https://a.pool.eternitywall.com", "https://ots.btc.catallaxy.com")
MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
VERSION = 1
OP_SHA256, OP_APPEND, OP_PREPEND = 0x08, 0xF0, 0xF1
UNARY = {0x02: lambda m: hashlib.sha1(m).digest(), 0x03: lambda m: hashlib.new("ripemd160", m).digest(),
         0x08: lambda m: hashlib.sha256(m).digest(), 0xF2: lambda m: m[::-1], 0xF3: lambda m: m.hex().encode()}
TAG_PENDING = bytes.fromhex("83dfe30d2ef90c8e")
TAG_BITCOIN = bytes.fromhex("0588960d73d71901")
TAG_LITECOIN = bytes.fromhex("06869a0d73d71b45")
MAX_RESPONSE = 10_000


# --------------------------------------------------------------------------------------- serialization
def _varuint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _varbytes(b: bytes) -> bytes:
    return _varuint(len(b)) + b


class _Reader:
    def __init__(self, data: bytes):
        self.f = io.BytesIO(data)

    def byte(self) -> int:
        b = self.f.read(1)
        if not b:
            raise ValueError("truncated timestamp")
        return b[0]

    def bytes(self, n: int) -> bytes:
        b = self.f.read(n)
        if len(b) != n:
            raise ValueError("truncated timestamp")
        return b

    def varuint(self) -> int:
        n, shift = 0, 0
        while True:
            b = self.byte()
            n |= (b & 0x7F) << shift
            if not b & 0x80:
                return n
            shift += 7

    def varbytes(self, maxlen: int = 8192) -> bytes:
        n = self.varuint()
        if n > maxlen:
            raise ValueError("field too long")
        return self.bytes(n)

    def at_end(self) -> bool:
        return self.f.read(1) == b""


def _apply(tag: int, arg: Optional[bytes], msg: bytes) -> bytes:
    if tag == OP_APPEND:
        return msg + arg
    if tag == OP_PREPEND:
        return arg + msg
    return UNARY[tag](msg)


def _item(r: _Reader, tag: int, msg: bytes, out: list, depth: int) -> None:
    """Parse one item (an op and its subtree, or an attestation) applied to ``msg``."""
    if tag == 0x00:
        atag = r.bytes(8)
        p = _Reader(r.varbytes())
        if atag == TAG_PENDING:
            out.append({"kind": "pending", "uri": p.varbytes(1000).decode("utf-8", "replace"), "msg": msg.hex()})
        elif atag in (TAG_BITCOIN, TAG_LITECOIN):
            out.append({"kind": "bitcoin" if atag == TAG_BITCOIN else "litecoin", "height": p.varuint(),
                        "msg": msg.hex()})
        else:
            out.append({"kind": "unknown", "tag": atag.hex(), "msg": msg.hex()})
    elif tag in (OP_APPEND, OP_PREPEND):
        _walk(r, _apply(tag, r.varbytes(4096), msg), out, depth + 1)
    elif tag in UNARY:
        _walk(r, _apply(tag, None, msg), out, depth + 1)
    else:
        raise ValueError(f"unknown op 0x{tag:02x}")


def _walk(r: _Reader, msg: bytes, out: list, depth: int = 0) -> None:
    """Parse one timestamp node for ``msg``; append every attestation reached, with the message it commits to."""
    if depth > 256:
        raise ValueError("timestamp too deep")
    tag = r.byte()
    while tag == 0xFF:
        _item(r, r.byte(), msg, out, depth)
        tag = r.byte()
    _item(r, tag, msg, out, depth)


def _split_top(ts: bytes, msg: bytes) -> list[bytes]:
    """The top-level items of a serialized timestamp (without their 0xff markers), so several calendars' answers can
    be merged under one node. Raises ValueError when the answer does not parse or carries no attestation."""
    r = _Reader(ts)
    items, out = [], []
    while True:
        tag = r.byte()
        last = tag != 0xFF
        if not last:
            tag = r.byte()
        start = r.f.tell() - 1
        _item(r, tag, msg, out, 0)
        items.append(ts[start:r.f.tell()])
        if last:
            break
    if not r.at_end():
        raise ValueError("trailing bytes after timestamp")
    if not out:
        raise ValueError("no attestation in the calendar's answer")
    return items


def _node(items: list[bytes]) -> bytes:
    return b"".join(b"\xff" + i for i in items[:-1]) + items[-1]


def detached(file_digest: bytes, nonce: bytes, calendar_answers: list[bytes]) -> bytes:
    """A detached .ots file: sha256(file) -> append(nonce) -> sha256 -> the calendars' answers merged."""
    if len(file_digest) != 32 or not calendar_answers:
        raise ValueError("need a 32-byte SHA-256 digest and at least one calendar answer")
    commit = hashlib.sha256(file_digest + nonce).digest()
    items = [it for ans in calendar_answers for it in _split_top(ans, commit)]
    return (MAGIC + _varuint(VERSION) + bytes([OP_SHA256]) + file_digest
            + bytes([OP_APPEND]) + _varbytes(nonce) + bytes([OP_SHA256]) + _node(items))


def info(ots: bytes) -> dict:
    """Parse a detached .ots file: the SHA-256 of the stamped file and every attestation, each with the message the
    path commits to (computed by replaying the ops)."""
    if not ots.startswith(MAGIC):
        raise ValueError("not an OpenTimestamps proof")
    r = _Reader(ots[len(MAGIC):])
    if r.varuint() != VERSION:
        raise ValueError("unsupported proof version")
    if r.byte() != OP_SHA256:
        raise ValueError("only SHA-256 file hashes are supported")
    digest = r.bytes(32)
    att: list = []
    _walk(r, digest, att)
    if not r.at_end():
        raise ValueError("trailing bytes after timestamp")
    return {"file_sha256": digest.hex(), "attestations": att,
            "pending": sorted({a["uri"] for a in att if a["kind"] == "pending"}),
            "bitcoin": sorted({a["height"] for a in att if a["kind"] == "bitcoin"})}


# --------------------------------------------------------------------------------------- calendars
def post_digest(calendar: str, digest: bytes, timeout: float = 10.0) -> bytes:
    """POST <calendar>/digest: the calendar's commitment path for ``digest`` (a serialized timestamp)."""
    req = urllib.request.Request(calendar.rstrip("/") + "/digest", data=digest, method="POST",
                                 headers={"Accept": "application/vnd.opentimestamps.v1",
                                          "User-Agent": "twohands-ots/1",
                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:   # noqa: S310 (fixed https calendar URLs)
        if resp.status != 200:
            raise OSError(f"{calendar}: HTTP {resp.status}")
        return resp.read(MAX_RESPONSE + 1)[:MAX_RESPONSE]


def stamp_bytes(data: bytes, calendars=CALENDARS, post: Callable[[str, bytes], bytes] = post_digest,
                nonce: Optional[bytes] = None, minimum: int = 1) -> tuple[bytes, list[str]]:
    """Stamp ``data`` as ``ots stamp`` stamps a file. Returns the .ots bytes and the calendars that answered.
    Raises OSError when fewer than ``minimum`` calendars answer with a valid timestamp."""
    file_digest = hashlib.sha256(data).digest()
    nonce = nonce if nonce is not None else os.urandom(16)
    commit = hashlib.sha256(file_digest + nonce).digest()
    answers, ok, errors = [], [], []
    for cal in calendars:
        try:
            ans = post(cal, commit)
            _split_top(ans, commit)          # reject an answer that does not parse
            answers.append(ans)
            ok.append(cal)
        except Exception as e:  # noqa: BLE001 (any calendar failure: try the next one)
            errors.append(f"{cal}: {e}")
    if len(ok) < minimum:
        raise OSError("no OpenTimestamps calendar answered: " + "; ".join(errors))
    return detached(file_digest, nonce, answers), ok


def stamp_file(path: str | Path, **kw) -> dict:
    """``ots stamp <path>``: writes <path>.ots and <path>.ots.json (when and where it was submitted)."""
    p = Path(path)
    ots, ok = stamp_bytes(p.read_bytes(), **kw)
    p.with_name(p.name + ".ots").write_bytes(ots)
    meta = {"submitted": datetime.now(timezone.utc).isoformat(timespec="seconds"), "calendars": ok,
            "file": p.name, "file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "verify": f"ots verify {p.name}.ots   (after a few hours: ots upgrade {p.name}.ots)"}
    p.with_name(p.name + ".ots.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    return meta


def status(path: str | Path) -> Optional[dict]:
    """What the report shows for a stamped file: the submission date, the calendars, any Bitcoin block heights, and
    whether the proof matches the file. None when there is no proof."""
    p = Path(path)
    po = p.with_name(p.name + ".ots")
    if not po.is_file() or not p.is_file():
        return None
    try:
        i = info(po.read_bytes())
    except ValueError:
        return None
    meta = {}
    pm = p.with_name(p.name + ".ots.json")
    if pm.is_file():
        try:
            meta = json.loads(pm.read_text(encoding="utf-8"))
        except ValueError:
            meta = {}
    return {"date": (meta.get("submitted") or "")[:10] or None, "submitted": meta.get("submitted"),
            "pending": i["pending"], "bitcoin": i["bitcoin"],
            "matches": i["file_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()}
