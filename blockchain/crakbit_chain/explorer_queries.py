from __future__ import annotations

import json

from .storage import Ledger


def explorer_summary(ledger: Ledger) -> dict:
    with ledger.connect() as conn:
        block_count = int(conn.execute("SELECT COUNT(*) AS n FROM blocks").fetchone()["n"])
        tx_count = int(conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"])
        account_count = int(conn.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"])
        issued = int(conn.execute("SELECT COALESCE(SUM(balance),0) AS n FROM accounts").fetchone()["n"])
    return {
        "chain_id": ledger.genesis.chain_id,
        "network": ledger.genesis.network_name,
        "symbol": ledger.genesis.symbol,
        "decimals": ledger.genesis.decimals,
        "height": ledger.height,
        "last_hash": ledger.last_hash,
        "stored_blocks": block_count,
        "stored_transactions": tx_count,
        "accounts": account_count,
        "issued_atomic_units": issued,
        "max_supply_atomic_units": ledger.genesis.max_supply,
    }


def recent_blocks(ledger: Ledger, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    with ledger.connect() as conn:
        rows = conn.execute(
            "SELECT height,hash,body FROM blocks ORDER BY height DESC LIMIT ?",
            (limit,),
        ).fetchall()
    result: list[dict] = []
    for row in rows:
        body = json.loads(row["body"])
        result.append(
            {
                "height": int(row["height"]),
                "hash": str(row["hash"]),
                "previous_hash": str(body.get("previous_hash", "")),
                "timestamp": int(body.get("timestamp", 0)),
                "round": int(body.get("round", 0)),
                "proposer": str(body.get("proposer", "")),
                "transaction_count": len(body.get("transactions", [])),
                "tx_root": str(body.get("tx_root", "")),
                "state_root": str(body.get("state_root", "")),
            }
        )
    return result


def account_activity(ledger: Ledger, address: str, limit: int = 50) -> dict:
    limit = max(1, min(int(limit), 100))
    # Bound the scan so this read-only helper cannot accidentally become an unbounded
    # historical query on a public RPC. A dedicated indexed explorer can replace this.
    scan_cap = max(500, limit * 20)
    with ledger.connect() as conn:
        rows = conn.execute(
            "SELECT txid,height,body FROM transactions ORDER BY height DESC, rowid DESC LIMIT ?",
            (scan_cap,),
        ).fetchall()
    items: list[dict] = []
    for row in rows:
        tx = json.loads(row["body"])
        if tx.get("sender") != address and tx.get("recipient") != address:
            continue
        items.append(
            {
                "txid": str(row["txid"]),
                "height": int(row["height"]),
                "direction": "out" if tx.get("sender") == address else "in",
                "sender": str(tx.get("sender", "")),
                "recipient": str(tx.get("recipient", "")),
                "amount": int(tx.get("amount", 0)),
                "fee": int(tx.get("fee", 0)),
                "nonce": int(tx.get("nonce", 0)),
                "memo": str(tx.get("memo", "")),
            }
        )
        if len(items) >= limit:
            break
    return {
        "account": ledger.account(address),
        "activity": items,
        "activity_limit": limit,
        "historical_scan_cap": scan_cap,
        "fully_indexed_history": False,
    }
