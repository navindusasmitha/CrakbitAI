from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .randomx_v33 import (
    RANDOMX_ALGO_CANDIDATE,
    XMRIG_NONCE_OFFSET,
    RandomXContext,
    RandomXV33Error,
    randomx_candidate_blob,
    xmrig_target_from_full_target,
)

XMRIG_ALGO_NAME = "rx/0"


class XmrigV33Error(ValueError):
    pass


@dataclass(frozen=True)
class XmrigCandidateJob:
    job_id: str
    blob: str
    target: str
    height: int
    seed_hash: str
    algo: str = XMRIG_ALGO_NAME

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "blob": self.blob,
            "target": self.target,
            "height": self.height,
            "seed_hash": self.seed_hash,
            "algo": self.algo,
        }


def build_xmrig_candidate_job(
    *,
    job_id: str,
    header: dict[str, Any],
    seed_hash: str,
    full_target: int,
) -> dict[str, Any]:
    if not job_id:
        raise XmrigV33Error("job_id is required")
    try:
        seed = bytes.fromhex(seed_hash)
    except ValueError as exc:
        raise XmrigV33Error("seed_hash must be hexadecimal") from exc
    if len(seed) != 32:
        raise XmrigV33Error("seed_hash must be 32 bytes")
    blob = randomx_candidate_blob(header)
    if len(blob) <= XMRIG_NONCE_OFFSET + 3:
        raise XmrigV33Error("candidate blob is too small for XMRig nonce offset")
    job = XmrigCandidateJob(
        job_id=str(job_id),
        blob=blob.hex(),
        target=xmrig_target_from_full_target(int(full_target)),
        height=int(header.get("height", 0)),
        seed_hash=seed_hash.lower(),
    )
    return {
        "format": "crakbit-xmrig-randomx-candidate/1",
        "job": job.to_dict(),
        "randomx_algorithm": RANDOMX_ALGO_CANDIDATE,
        "nonce_offset": XMRIG_NONCE_OFFSET,
        "consensus_enabled": False,
        "note": "Protocol candidate only. Current Crakbit v0.33 consensus remains crakpow-scrypt-v1 until algorithm review/freeze.",
        "production_mainnet_ready": False,
    }


def parse_xmrig_submit(payload: dict[str, Any]) -> dict[str, str]:
    params = payload.get("params", payload)
    if not isinstance(params, dict):
        raise XmrigV33Error("XMRig submit params must be an object")
    job_id = str(params.get("job_id", ""))
    nonce = str(params.get("nonce", "")).lower()
    result = str(params.get("result", "")).lower()
    if not job_id:
        raise XmrigV33Error("submit job_id missing")
    try:
        nonce_raw = bytes.fromhex(nonce)
        result_raw = bytes.fromhex(result)
    except ValueError as exc:
        raise XmrigV33Error("submit nonce/result must be hexadecimal") from exc
    if len(nonce_raw) != 4:
        raise XmrigV33Error("XMRig RandomX nonce must be 4 bytes")
    if len(result_raw) != 32:
        raise XmrigV33Error("XMRig result must be 32 bytes")
    return {"job_id": job_id, "nonce": nonce, "result": result}


def verify_xmrig_candidate_submit(
    *,
    job_record: dict[str, Any],
    submit_payload: dict[str, Any],
    library_path: str | Path | None = None,
    mode: str = "light",
) -> dict[str, Any]:
    job = job_record.get("job", job_record)
    if not isinstance(job, dict):
        raise XmrigV33Error("job record missing job object")
    submit = parse_xmrig_submit(submit_payload)
    if submit["job_id"] != str(job.get("job_id", "")):
        raise XmrigV33Error("submit job_id mismatch")
    try:
        blob = bytearray(bytes.fromhex(str(job["blob"])))
        seed = bytes.fromhex(str(job["seed_hash"]))
        target_bytes = bytes.fromhex(str(job["target"]))
    except (KeyError, ValueError) as exc:
        raise XmrigV33Error("invalid candidate job encoding") from exc
    if len(seed) != 32 or len(target_bytes) != 8:
        raise XmrigV33Error("invalid seed/target length")
    nonce_raw = bytes.fromhex(submit["nonce"])
    blob[XMRIG_NONCE_OFFSET : XMRIG_NONCE_OFFSET + 4] = nonce_raw

    try:
        with RandomXContext(seed, library_path=library_path, mode=mode) as ctx:
            digest = ctx.hash(bytes(blob))
            library = ctx.library_path
    except RandomXV33Error:
        raise

    submitted = bytes.fromhex(submit["result"])
    target64 = int.from_bytes(target_bytes, "little")
    value64 = int.from_bytes(digest[24:32], "little")
    hash_match = digest == submitted
    share_target_met = value64 < target64
    return {
        "job_id": submit["job_id"],
        "hash_match": hash_match,
        "share_target_met": share_target_met,
        "accepted_candidate_share": bool(hash_match and share_target_met),
        "calculated_hash": digest.hex(),
        "submitted_hash": submitted.hex(),
        "target64": str(target64),
        "value64": str(value64),
        "library_path": library,
        "mode": mode,
        "consensus_enabled": False,
        "production_mainnet_ready": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise XmrigV33Error("JSON file must contain an object")
    return data
