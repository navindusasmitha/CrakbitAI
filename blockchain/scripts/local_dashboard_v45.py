from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from fastapi import HTTPException, Request
from pydantic import BaseModel

import local_dashboard_v39 as base
import local_dashboard_v41 as ui
import local_dashboard_v43 as explorer
import local_dashboard_v44 as v44
from crakbit_chain.crypto import KeyPair, address_from_public_key, canonical_json, verify_signature
from crakbit_chain.pow_v31 import COIN, build_unsigned_transaction, sign_transaction


USER_WALLET_DIR = Path("/wallet-data")
BACKUP_DIR = Path("/wallet-backups")
GUARD_DB = USER_WALLET_DIR / "dashboard-wallet-guard.sqlite3"
STATIC_LABELS = {"pool-hot", "miner1", "miner2"}
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
BACKUP_FORMAT = "crakbit-local-wallet-backup-v1"
DUPLICATE_WINDOW_MS = 90_000
WRITE_LOCK = threading.Lock()


class WalletCreateRequest(BaseModel):
    label: str


class WalletBackupRequest(BaseModel):
    passphrase: str


class WalletRestoreRequest(BaseModel):
    backup_file: str
    passphrase: str
    label: str


class WalletSendV45Request(BaseModel):
    wallet: str
    to_address: str
    amount_crk: str
    fee_crk: str = "0.00010000"


def _label(value: str) -> str:
    text = str(value).strip().lower()
    if not LABEL_RE.fullmatch(text):
        raise ValueError("wallet label must be 1-32 chars: lowercase letters, digits, _ or -")
    return text


def _user_wallet_path(label: str) -> Path:
    return USER_WALLET_DIR / f"{_label(label)}.json"


def _register_user_wallets() -> None:
    USER_WALLET_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in USER_WALLET_DIR.glob("*.json"):
        label = path.stem.lower()
        if LABEL_RE.fullmatch(label) and label not in STATIC_LABELS:
            ui.WALLET_FILES[label] = path


def _init_guard_db() -> None:
    USER_WALLET_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(GUARD_DB)
    try:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS send_guard(
                fingerprint TEXT PRIMARY KEY,
                last_success_ms INTEGER NOT NULL,
                response_json TEXT NOT NULL
            )
            """
        )
        db.commit()
    finally:
        db.close()


def _write_allowed(request: Request) -> None:
    if request.headers.get("x-crakbit-local-token", "") != ui.LOCAL_WRITE_TOKEN:
        raise HTTPException(status_code=403, detail="local write token rejected")


def _backup_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < 12:
        raise ValueError("backup passphrase must contain at least 12 characters")
    return Scrypt(salt=salt, length=32, n=32768, r=8, p=1).derive(passphrase.encode("utf-8"))


def _encrypt_backup(keypair: KeyPair, passphrase: str) -> dict[str, Any]:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _backup_key(passphrase, salt)
    aad = f"{BACKUP_FORMAT}:{keypair.address}".encode("utf-8")
    private_payload = canonical_json(
        {
            "private_key": keypair.private_key_b64,
            "public_key": keypair.public_key_b64,
            "address": keypair.address,
        }
    )
    ciphertext = AESGCM(key).encrypt(nonce, private_payload, aad)
    return {
        "format": BACKUP_FORMAT,
        "address": keypair.address,
        "public_key": keypair.public_key_b64,
        "kdf": {
            "name": "scrypt",
            "n": 32768,
            "r": 8,
            "p": 1,
            "salt_b64": base64.b64encode(salt).decode("ascii"),
        },
        "cipher": {
            "name": "AES-256-GCM",
            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        },
        "local_rehearsal_only": True,
        "production_mainnet_ready": False,
    }


def _decrypt_backup(record: dict[str, Any], passphrase: str) -> KeyPair:
    if record.get("format") != BACKUP_FORMAT:
        raise ValueError("unsupported wallet backup format")
    kdf = dict(record.get("kdf") or {})
    cipher = dict(record.get("cipher") or {})
    if kdf.get("name") != "scrypt" or cipher.get("name") != "AES-256-GCM":
        raise ValueError("unsupported wallet backup algorithms")
    salt = base64.b64decode(str(kdf["salt_b64"]), validate=True)
    nonce = base64.b64decode(str(cipher["nonce_b64"]), validate=True)
    ciphertext = base64.b64decode(str(cipher["ciphertext_b64"]), validate=True)
    address = str(record["address"])
    key = _backup_key(passphrase, salt)
    aad = f"{BACKUP_FORMAT}:{address}".encode("utf-8")
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    data = json.loads(plaintext.decode("utf-8"))
    public_key = str(data["public_key"])
    derived = address_from_public_key(public_key)
    if derived != address or str(data.get("address")) != address:
        raise ValueError("backup address validation failed")
    pair = KeyPair(str(data["private_key"]), public_key, address)
    challenge = b"crakbit-local-wallet-restore-check-v1"
    if not verify_signature(pair.public_key_b64, challenge, pair.sign(challenge)):
        raise ValueError("backup private/public key validation failed")
    return pair


def _save_pair(pair: KeyPair, path: Path) -> None:
    if path.exists():
        raise ValueError("wallet label already exists")
    pair.save(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _load_pair(label: str) -> KeyPair:
    text = _label(label)
    path = ui.WALLET_FILES.get(text)
    if path is None:
        candidate = _user_wallet_path(text)
        if candidate.is_file():
            ui.WALLET_FILES[text] = candidate
            path = candidate
    if path is None:
        raise ValueError("unknown local wallet")
    return KeyPair.load(path)


def _mature_utxos(address: str) -> list[dict[str, Any]]:
    def read(db: sqlite3.Connection) -> list[dict[str, Any]]:
        tip = db.execute("SELECT height FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
        if tip is None:
            raise RuntimeError("chain has no blocks")
        tip_height = int(tip["height"])
        meta = {str(row["key"]): str(row["value"]) for row in db.execute("SELECT key,value FROM meta")}
        config = json.loads(meta.get("config", "{}"))
        maturity = int(config.get("coinbase_maturity", 0))
        rows = db.execute(
            "SELECT txid,vout,address,amount,coinbase_height FROM utxos WHERE address=? ORDER BY amount DESC, txid, vout",
            (address,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            coinbase_height = row["coinbase_height"]
            mature = coinbase_height is None or (tip_height - int(coinbase_height)) >= maturity
            result.append(
                {
                    "txid": str(row["txid"]),
                    "vout": int(row["vout"]),
                    "address": str(row["address"]),
                    "amount": int(row["amount"]),
                    "coinbase_height": None if coinbase_height is None else int(coinbase_height),
                    "mature": bool(mature),
                }
            )
        return result

    return explorer._with_node_db(read)


def _send_fingerprint(wallet: str, to_address: str, amount: int, fee: int) -> str:
    body = canonical_json(
        {
            "wallet": wallet,
            "to_address": to_address,
            "amount": amount,
            "fee": fee,
        }
    )
    return hashlib.sha256(body).hexdigest()


def _guard_lookup(fingerprint: str) -> dict[str, Any] | None:
    db = sqlite3.connect(GUARD_DB)
    try:
        row = db.execute(
            "SELECT last_success_ms,response_json FROM send_guard WHERE fingerprint=?",
            (fingerprint,),
        ).fetchone()
        if row is None:
            return None
        age = int(time.time() * 1000) - int(row[0])
        if age > DUPLICATE_WINDOW_MS:
            return None
        result = json.loads(str(row[1]))
        result["duplicate_suppressed"] = True
        result["duplicate_guard_age_ms"] = max(0, age)
        return result
    finally:
        db.close()


def _guard_store(fingerprint: str, result: dict[str, Any]) -> None:
    db = sqlite3.connect(GUARD_DB)
    try:
        db.execute(
            "INSERT INTO send_guard(fingerprint,last_success_ms,response_json) VALUES(?,?,?) "
            "ON CONFLICT(fingerprint) DO UPDATE SET last_success_ms=excluded.last_success_ms,response_json=excluded.response_json",
            (fingerprint, int(time.time() * 1000), json.dumps(result, sort_keys=True)),
        )
        db.commit()
    finally:
        db.close()


def _history(label: str, limit: int) -> dict[str, Any]:
    key = _load_pair(label)
    address = key.address
    limit = max(1, min(int(limit), 100))

    def read(db: sqlite3.Connection) -> dict[str, Any]:
        rows = db.execute(
            "SELECT txid,block_height,tx_index,tx_json FROM transactions ORDER BY block_height DESC, tx_index DESC"
        ).fetchall()
        history: list[dict[str, Any]] = []
        for row in rows:
            tx = json.loads(str(row["tx_json"]))
            outputs = list(tx.get("outputs") or [])
            own_outputs = sum(int(item.get("amount", 0)) for item in outputs if str(item.get("address")) == address)
            input_owned = False
            input_total = 0
            for item in list(tx.get("inputs") or []):
                public_key = str(item.get("public_key", ""))
                try:
                    if public_key and address_from_public_key(public_key) == address:
                        input_owned = True
                except Exception:
                    pass
                prev = db.execute("SELECT tx_json FROM transactions WHERE txid=?", (str(item.get("txid", "")),)).fetchone()
                if prev is not None:
                    prev_tx = json.loads(str(prev[0]))
                    vout = int(item.get("vout", -1))
                    prev_outputs = list(prev_tx.get("outputs") or [])
                    if 0 <= vout < len(prev_outputs):
                        input_total += int(prev_outputs[vout].get("amount", 0))
            if not input_owned and own_outputs <= 0:
                continue
            total_outputs = sum(int(item.get("amount", 0)) for item in outputs)
            fee = 0 if bool(tx.get("coinbase")) else max(0, input_total - total_outputs)
            if input_owned:
                sent = sum(int(item.get("amount", 0)) for item in outputs if str(item.get("address")) != address)
                direction = "outgoing"
                amount = sent
            else:
                direction = "incoming"
                amount = own_outputs
            history.append(
                {
                    "txid": str(row["txid"]),
                    "block_height": int(row["block_height"]),
                    "tx_index": int(row["tx_index"]),
                    "direction": direction,
                    "amount_atoms": amount,
                    "amount_crk": ui._crk(amount),
                    "fee_atoms": fee,
                    "fee_crk": ui._crk(fee),
                    "change_or_received_to_self_atoms": own_outputs,
                    "coinbase": bool(tx.get("coinbase")),
                }
            )
            if len(history) >= limit:
                break
        return {
            "label": label,
            "address": address,
            "transactions": history,
            "history_source": "node1-read-only-sqlite",
            "production_mainnet_ready": False,
        }

    return explorer._with_node_db(read)


_register_user_wallets()
_init_guard_db()


@base.app.post("/api/v45/wallet/create")
def api_wallet_create(payload: WalletCreateRequest, request: Request) -> dict[str, Any]:
    _write_allowed(request)
    try:
        label = _label(payload.label)
        if label in STATIC_LABELS or label in ui.WALLET_FILES:
            raise ValueError("wallet label already exists or is reserved")
        path = _user_wallet_path(label)
        pair = KeyPair.generate()
        _save_pair(pair, path)
        ui.WALLET_FILES[label] = path
        return {
            "created": True,
            "label": label,
            "address": pair.address,
            "private_key_exposed": False,
            "wallet_storage": "local-user-wallet-data",
            "local_only": True,
            "production_mainnet_ready": False,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@base.app.post("/api/v45/wallet/{label}/backup")
def api_wallet_backup(label: str, payload: WalletBackupRequest, request: Request) -> dict[str, Any]:
    _write_allowed(request)
    try:
        pair = _load_pair(label)
        backup = _encrypt_backup(pair, payload.passphrase)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        filename = f"{_label(label)}-{stamp}.crkbak.json"
        path = BACKUP_DIR / filename
        path.write_text(json.dumps(backup, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return {
            "saved": True,
            "label": _label(label),
            "address": pair.address,
            "backup_file": filename,
            "backup_format": BACKUP_FORMAT,
            "encrypted": True,
            "passphrase_stored": False,
            "private_key_exposed": False,
            "local_only": True,
            "production_mainnet_ready": False,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@base.app.get("/api/v45/backups")
def api_wallet_backups() -> dict[str, Any]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(BACKUP_DIR.glob("*.crkbak.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            files.append(
                {
                    "backup_file": path.name,
                    "address": data.get("address"),
                    "format": data.get("format"),
                    "size_bytes": path.stat().st_size,
                }
            )
        except Exception:
            files.append({"backup_file": path.name, "valid_json": False, "size_bytes": path.stat().st_size})
    return {"backups": files, "local_only": True, "production_mainnet_ready": False}


@base.app.post("/api/v45/wallet/restore")
def api_wallet_restore(payload: WalletRestoreRequest, request: Request) -> dict[str, Any]:
    _write_allowed(request)
    try:
        filename = Path(str(payload.backup_file)).name
        if filename != str(payload.backup_file) or not filename.endswith(".crkbak.json"):
            raise ValueError("invalid backup filename")
        backup_path = BACKUP_DIR / filename
        if not backup_path.is_file():
            raise ValueError("backup file not found")
        label = _label(payload.label)
        if label in STATIC_LABELS or label in ui.WALLET_FILES or _user_wallet_path(label).exists():
            raise ValueError("wallet label already exists or is reserved")
        record = json.loads(backup_path.read_text(encoding="utf-8"))
        pair = _decrypt_backup(record, payload.passphrase)
        path = _user_wallet_path(label)
        _save_pair(pair, path)
        ui.WALLET_FILES[label] = path
        return {
            "restored": True,
            "label": label,
            "address": pair.address,
            "source_backup": filename,
            "private_key_exposed": False,
            "local_only": True,
            "production_mainnet_ready": False,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@base.app.get("/api/v45/wallet/{label}/history")
def api_wallet_history(label: str, limit: int = 25) -> dict[str, Any]:
    try:
        return _history(label, limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@base.app.post("/api/v45/wallet/send")
def api_wallet_send_v45(payload: WalletSendV45Request, request: Request) -> dict[str, Any]:
    _write_allowed(request)
    try:
        wallet = _label(payload.wallet)
        if not payload.to_address.startswith("crk1") or len(payload.to_address) < 20:
            raise ValueError("invalid destination address")
        amount = ui._atoms(payload.amount_crk)
        fee = ui._atoms(payload.fee_crk, allow_zero=True)
        pair = _load_pair(wallet)
        if payload.to_address == pair.address:
            raise ValueError("destination must differ from source wallet")
        fingerprint = _send_fingerprint(wallet, payload.to_address, amount, fee)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with WRITE_LOCK:
        duplicate = _guard_lookup(fingerprint)
        if duplicate is not None:
            return duplicate
        try:
            selected: list[dict[str, Any]] = []
            total = 0
            for utxo in _mature_utxos(pair.address):
                if not utxo["mature"]:
                    continue
                selected.append(utxo)
                total += int(utxo["amount"])
                if total >= amount + fee:
                    break
            if total < amount + fee:
                raise ValueError("insufficient confirmed on-chain funds")
            outputs: list[dict[str, Any]] = [{"address": payload.to_address, "amount": amount}]
            change = total - amount - fee
            if change:
                outputs.append({"address": pair.address, "amount": change})
            unsigned = build_unsigned_transaction(
                [{"txid": item["txid"], "vout": int(item["vout"])} for item in selected],
                outputs,
            )
            signed = sign_transaction(unsigned, pair, selected)
            submitted = ui._post_json(f"{ui.NODE1}/pow/v2/submittransaction", {"transaction": signed}, timeout=12.0)
            result = {
                "accepted": bool(submitted.get("accepted")),
                "txid": submitted.get("txid"),
                "fee_atoms": int(submitted.get("fee", fee)),
                "fee_crk": ui._crk(int(submitted.get("fee", fee))),
                "from_wallet": wallet,
                "from_address": pair.address,
                "to_address": payload.to_address,
                "amount_atoms": amount,
                "amount_crk": ui._crk(amount),
                "duplicate_suppressed": False,
                "duplicate_window_seconds": DUPLICATE_WINDOW_MS // 1000,
                "private_key_exposed": False,
                "local_only": True,
                "production_mainnet_ready": False,
            }
            if not result["accepted"]:
                raise ValueError(str(submitted))
            _guard_store(fingerprint, result)
            return result
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


def collect_status() -> dict[str, Any]:
    status = v44.collect_status()
    status["format"] = "crakbit-local-dashboard-v45/1"
    status["source_commit"] = os.environ.get("CRAKBIT_SOURCE_COMMIT", "unknown")
    status["wallet_lifecycle"] = {
        "user_wallet_storage": "local-bind-mount",
        "encrypted_backup": "AES-256-GCM+scrypt",
        "transaction_history_source": "node1-read-only-sqlite",
        "duplicate_send_guard_seconds": DUPLICATE_WINDOW_MS // 1000,
        "private_keys_returned_by_api": False,
        "production_mainnet_ready": False,
    }
    return status


base.collect_status = collect_status
base.app.version = "0.45.0-local"
base.INDEX_HTML = base.INDEX_HTML.replace("v0.44", "v0.45")
# Route the existing Wallets-tab Send button through the guarded v0.45 endpoint.
base.INDEX_HTML = base.INDEX_HTML.replace("/api/v41/wallet/send", "/api/v45/wallet/send")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local-only rehearsal dashboard v0.45")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=38080)
    parser.add_argument("--auto-evidence-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.auto_evidence_seconds > 0:
        threading.Thread(target=base._auto_snapshot_loop, args=(args.auto_evidence_seconds,), daemon=True).start()
    uvicorn.run(base.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
