from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from .crypto import canonical_json, sha256_hex
from .validator_governance_v21 import GOVERNANCE_FORMAT


class GovernanceBroadcastError(RuntimeError):
    pass


def governance_tx_bytes(envelope: dict[str, Any]) -> bytes:
    if envelope.get("type") != "validator_governance":
        raise GovernanceBroadcastError("transaction is not a validator-governance envelope")
    if envelope.get("format") != GOVERNANCE_FORMAT:
        raise GovernanceBroadcastError("unsupported validator-governance transaction format")
    request = envelope.get("request")
    if not isinstance(request, dict):
        raise GovernanceBroadcastError("governance request is missing")
    if int(request.get("emit_height", 0)) < 1:
        raise GovernanceBroadcastError("governance emit_height is invalid")
    return canonical_json(envelope)


def build_broadcast_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    tx = governance_tx_bytes(envelope)
    return {
        "jsonrpc": "2.0",
        "id": "crakbit-v22-governance",
        "method": "broadcast_tx_sync",
        # CometBFT JSON encodes []byte values as base64 strings.
        "params": {"tx": base64.b64encode(tx).decode("ascii")},
    }


def _latest_height(client: httpx.Client, rpc_url: str) -> int:
    response = client.get(rpc_url.rstrip("/") + "/status")
    response.raise_for_status()
    body = response.json()
    try:
        return int(body["result"]["sync_info"]["latest_block_height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GovernanceBroadcastError("CometBFT status response is missing latest block height") from exc


def guarded_broadcast_governance(
    envelope: dict[str, Any],
    *,
    rpc_url: str,
    wait_for_preheight: bool = False,
    wait_timeout_seconds: float = 60.0,
    poll_seconds: float = 0.5,
    request_timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    tx = governance_tx_bytes(envelope)
    emit_height = int(envelope["request"]["emit_height"])
    preheight = emit_height - 1
    if preheight < 0:
        raise GovernanceBroadcastError("invalid governance pre-emission height")
    deadline = time.monotonic() + float(wait_timeout_seconds)

    with httpx.Client(timeout=request_timeout_seconds) as client:
        while True:
            latest = _latest_height(client, rpc_url)
            if latest == preheight:
                break
            if latest > preheight:
                raise GovernanceBroadcastError(
                    f"network already passed governance pre-height {preheight}; latest height is {latest}"
                )
            if not wait_for_preheight:
                raise GovernanceBroadcastError(
                    f"refusing early governance broadcast: latest height {latest}, expected {preheight}"
                )
            if time.monotonic() >= deadline:
                raise GovernanceBroadcastError(
                    f"timed out waiting for governance pre-height {preheight}; latest height is {latest}"
                )
            time.sleep(max(0.05, min(float(poll_seconds), 5.0)))

        payload = build_broadcast_payload(envelope)
        response = client.post(rpc_url.rstrip("/"), json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise GovernanceBroadcastError(f"CometBFT RPC error: {body['error']}")
        result = body.get("result") or {}
        code = int(result.get("code", 0))
        log = str(result.get("log", ""))
        tx_hash = str(result.get("hash", ""))
        if code != 0:
            raise GovernanceBroadcastError(
                f"governance transaction rejected by CheckTx with code {code}: {log}"
            )
        return {
            "broadcast": True,
            "rpc_url": rpc_url,
            "observed_preheight": preheight,
            "emit_height": emit_height,
            "change_id": str(envelope.get("change_id", "")),
            "local_tx_sha256": sha256_hex(tx),
            "cometbft_tx_hash": tx_hash,
            "check_tx_code": code,
            "check_tx_log": log,
            "finalize_inclusion_verified": False,
            "production_mainnet_ready": False,
        }
