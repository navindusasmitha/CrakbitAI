from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex
from .pow_v31 import COIN, PowChain, PowV31Error, build_unsigned_transaction, sign_transaction, transaction_id


class PoolPayoutV34Error(ValueError):
    pass


def _pool_db(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(Path(path))
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS payout_plans_v34(
            plan_id TEXT PRIMARY KEY,
            created_at_ms INTEGER NOT NULL,
            wallet_address TEXT NOT NULL,
            txid TEXT NOT NULL UNIQUE,
            transaction_json TEXT NOT NULL,
            payouts_json TEXT NOT NULL,
            total_payout INTEGER NOT NULL,
            fee INTEGER NOT NULL,
            state TEXT NOT NULL,
            confirmed_height INTEGER,
            finalized_at_ms INTEGER
        );
        """
    )
    db.commit()
    return db


def _balances(db: sqlite3.Connection) -> dict[str, int]:
    try:
        rows = db.execute("SELECT payout_address,pending_amount FROM balances ORDER BY payout_address").fetchall()
    except sqlite3.OperationalError as exc:
        raise PoolPayoutV34Error("pool DB is missing PPLNS balances; run the pool first") from exc
    return {str(row["payout_address"]): int(row["pending_amount"]) for row in rows}


def _existing_reserved(db: sqlite3.Connection) -> dict[str, int]:
    reserved: dict[str, int] = {}
    rows = db.execute(
        "SELECT payouts_json FROM payout_plans_v34 WHERE state IN ('built','submitted')"
    ).fetchall()
    for row in rows:
        for item in json.loads(row["payouts_json"]):
            address = str(item["address"])
            reserved[address] = reserved.get(address, 0) + int(item["amount"])
    return reserved


def build_payout_plan(
    *,
    chain_db: str | Path,
    pool_db: str | Path,
    wallet_path: str | Path,
    minimum_payout: int,
    fee: int,
    max_recipients: int = 100,
    max_total_payout: int | None = None,
) -> dict[str, Any]:
    minimum_payout = int(minimum_payout)
    fee = int(fee)
    max_recipients = int(max_recipients)
    if minimum_payout <= 0 or fee < 0:
        raise PoolPayoutV34Error("invalid payout threshold/fee")
    if max_recipients < 1 or max_recipients > 1000:
        raise PoolPayoutV34Error("max recipients must be 1..1000")
    if max_total_payout is not None and int(max_total_payout) <= 0:
        raise PoolPayoutV34Error("max total payout must be positive")

    wallet = KeyPair.load(wallet_path)
    pool = _pool_db(pool_db)
    chain = PowChain(chain_db)
    try:
        balances = _balances(pool)
        reserved = _existing_reserved(pool)
        claims: list[dict[str, int | str]] = []
        for address, pending in sorted(balances.items()):
            available_claim = max(0, int(pending) - int(reserved.get(address, 0)))
            if available_claim >= minimum_payout:
                claims.append({"address": address, "amount": available_claim})
        claims = claims[:max_recipients]
        if not claims:
            raise PoolPayoutV34Error("no unreserved PPLNS balance meets the payout threshold")

        mature_utxos = [item for item in chain.get_utxos(wallet.address) if item["mature"]]
        wallet_available = sum(int(item["amount"]) for item in mature_utxos)
        spendable_for_payouts = wallet_available - fee
        if spendable_for_payouts <= 0:
            raise PoolPayoutV34Error("pool hot wallet has no mature funds available after fee")
        if max_total_payout is not None:
            spendable_for_payouts = min(spendable_for_payouts, int(max_total_payout))

        payouts: list[dict[str, Any]] = []
        remaining = spendable_for_payouts
        for claim in claims:
            amount = min(int(claim["amount"]), remaining)
            if amount < minimum_payout:
                continue
            payouts.append({"address": str(claim["address"]), "amount": amount})
            remaining -= amount
            if remaining < minimum_payout:
                break
        if not payouts:
            raise PoolPayoutV34Error("mature hot-wallet funds are below the payout threshold")

        total_payout = sum(int(item["amount"]) for item in payouts)
        required = total_payout + fee
        selected: list[dict[str, Any]] = []
        selected_total = 0
        for utxo in sorted(mature_utxos, key=lambda item: (-int(item["amount"]), item["txid"], item["vout"])):
            selected.append(utxo)
            selected_total += int(utxo["amount"])
            if selected_total >= required:
                break
        if selected_total < required:
            raise PoolPayoutV34Error("insufficient mature pool-wallet UTXOs")

        outputs = list(payouts)
        change = selected_total - required
        if change:
            outputs.append({"address": wallet.address, "amount": change})
        unsigned = build_unsigned_transaction(
            [{"txid": item["txid"], "vout": int(item["vout"])} for item in selected],
            outputs,
        )
        signed = sign_transaction(unsigned, wallet, selected)
        txid = transaction_id(signed)
        stable = {
            "format": "crakbit-pool-payout-plan-v34/1",
            "wallet_address": wallet.address,
            "txid": txid,
            "payouts": payouts,
            "total_payout": total_payout,
            "fee": fee,
            "selected_outpoints": [f"{item['txid']}:{item['vout']}" for item in selected],
        }
        plan_id = sha256_hex(canonical_json(stable))
        pool.execute(
            """
            INSERT INTO payout_plans_v34(plan_id,created_at_ms,wallet_address,txid,transaction_json,payouts_json,total_payout,fee,state)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                plan_id,
                int(time.time() * 1000),
                wallet.address,
                txid,
                json.dumps(signed, sort_keys=True),
                json.dumps(payouts, sort_keys=True),
                total_payout,
                fee,
                "built",
            ),
        )
        pool.commit()
        return {
            **stable,
            "plan_id": plan_id,
            "transaction": signed,
            "change": change,
            "mature_wallet_available": wallet_available,
            "minimum_payout": minimum_payout,
            "automatic_submit": False,
            "automatic_balance_debit": False,
            "production_mainnet_ready": False,
        }
    except sqlite3.IntegrityError as exc:
        pool.rollback()
        raise PoolPayoutV34Error("an equivalent payout transaction/plan already exists") from exc
    finally:
        chain.close()
        pool.close()


def list_payout_plans(pool_db: str | Path) -> list[dict[str, Any]]:
    db = _pool_db(pool_db)
    try:
        rows = db.execute("SELECT * FROM payout_plans_v34 ORDER BY created_at_ms DESC").fetchall()
        return [
            {
                "plan_id": str(row["plan_id"]),
                "created_at_ms": int(row["created_at_ms"]),
                "wallet_address": str(row["wallet_address"]),
                "txid": str(row["txid"]),
                "payouts": json.loads(row["payouts_json"]),
                "total_payout": int(row["total_payout"]),
                "fee": int(row["fee"]),
                "state": str(row["state"]),
                "confirmed_height": row["confirmed_height"],
            }
            for row in rows
        ]
    finally:
        db.close()


def payout_transaction(pool_db: str | Path, plan_id: str) -> dict[str, Any]:
    db = _pool_db(pool_db)
    try:
        row = db.execute("SELECT * FROM payout_plans_v34 WHERE plan_id=?", (str(plan_id),)).fetchone()
        if row is None:
            raise PoolPayoutV34Error("payout plan not found")
        return json.loads(row["transaction_json"])
    finally:
        db.close()


def mark_submitted(pool_db: str | Path, plan_id: str) -> dict[str, Any]:
    db = _pool_db(pool_db)
    try:
        row = db.execute("SELECT state,txid FROM payout_plans_v34 WHERE plan_id=?", (str(plan_id),)).fetchone()
        if row is None:
            raise PoolPayoutV34Error("payout plan not found")
        if str(row["state"]) == "finalized":
            raise PoolPayoutV34Error("payout plan is already finalized")
        db.execute("UPDATE payout_plans_v34 SET state='submitted' WHERE plan_id=?", (str(plan_id),))
        db.commit()
        return {"plan_id": str(plan_id), "txid": str(row["txid"]), "state": "submitted", "production_mainnet_ready": False}
    finally:
        db.close()


def reconcile_payout_plan(
    *,
    chain_db: str | Path,
    pool_db: str | Path,
    plan_id: str,
    minimum_confirmations: int = 2,
) -> dict[str, Any]:
    minimum_confirmations = max(1, int(minimum_confirmations))
    pool = _pool_db(pool_db)
    chain = PowChain(chain_db)
    try:
        row = pool.execute("SELECT * FROM payout_plans_v34 WHERE plan_id=?", (str(plan_id),)).fetchone()
        if row is None:
            raise PoolPayoutV34Error("payout plan not found")
        if str(row["state"]) == "finalized":
            return {
                "plan_id": str(plan_id),
                "txid": str(row["txid"]),
                "state": "finalized",
                "confirmations": minimum_confirmations,
                "idempotent": True,
                "production_mainnet_ready": False,
            }
        txid = str(row["txid"])
        confirmed = chain.db.execute("SELECT block_height FROM transactions WHERE txid=?", (txid,)).fetchone()
        if confirmed is None:
            mempool = chain.db.execute("SELECT 1 FROM mempool WHERE txid=?", (txid,)).fetchone()
            return {
                "plan_id": str(plan_id),
                "txid": txid,
                "state": "mempool" if mempool else str(row["state"]),
                "confirmations": 0,
                "finalized": False,
                "production_mainnet_ready": False,
            }
        height = int(confirmed["block_height"])
        tip = int(chain.tip()["height"])
        confirmations = max(0, tip - height + 1)
        if confirmations < minimum_confirmations:
            return {
                "plan_id": str(plan_id),
                "txid": txid,
                "state": "confirmed-pending-depth",
                "block_height": height,
                "confirmations": confirmations,
                "finalized": False,
                "production_mainnet_ready": False,
            }

        payouts = json.loads(row["payouts_json"])
        try:
            pool.execute("BEGIN IMMEDIATE")
            for item in payouts:
                address = str(item["address"])
                amount = int(item["amount"])
                balance = pool.execute("SELECT pending_amount FROM balances WHERE payout_address=?", (address,)).fetchone()
                if balance is None or int(balance["pending_amount"]) < amount:
                    raise PoolPayoutV34Error(f"pool balance changed below finalized payout for {address}")
                pool.execute(
                    "UPDATE balances SET pending_amount=pending_amount-? WHERE payout_address=?",
                    (amount, address),
                )
            pool.execute(
                "UPDATE payout_plans_v34 SET state='finalized',confirmed_height=?,finalized_at_ms=? WHERE plan_id=?",
                (height, int(time.time() * 1000), str(plan_id)),
            )
            pool.commit()
        except Exception:
            pool.rollback()
            raise
        return {
            "plan_id": str(plan_id),
            "txid": txid,
            "state": "finalized",
            "block_height": height,
            "confirmations": confirmations,
            "finalized": True,
            "debited_payout_total": int(row["total_payout"]),
            "production_mainnet_ready": False,
        }
    finally:
        chain.close()
        pool.close()


def atomic_to_crk(value: int) -> float:
    return int(value) / COIN
