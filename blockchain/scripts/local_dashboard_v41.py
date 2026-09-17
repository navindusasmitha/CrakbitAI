from __future__ import annotations

import argparse
import json
import secrets
import threading
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import HTTPException, Request
from pydantic import BaseModel

import local_dashboard_v39 as base
import local_dashboard_v40 as ops
from crakbit_chain.crypto import KeyPair
from crakbit_chain.pow_v31 import COIN, build_unsigned_transaction, sign_transaction


NODE1 = base.NODE_URLS["node1"].rstrip("/")
WALLET_ROOT = Path("/runtime/wallets")
WALLET_FILES = {
    "pool-hot": WALLET_ROOT / "pool-hot.json",
    "miner1": WALLET_ROOT / "miner1.json",
    "miner2": WALLET_ROOT / "miner2.json",
}
LOCAL_WRITE_TOKEN = secrets.token_urlsafe(32)
SEND_LOCK = threading.Lock()


class WalletSendRequest(BaseModel):
    wallet: str
    to_address: str
    amount_crk: str
    fee_crk: str = "0.00010000"


def _post_json(url: str, payload: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _atoms(text: str, *, allow_zero: bool = False) -> int:
    try:
        value = Decimal(str(text).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid CRK amount") from exc
    if not value.is_finite():
        raise ValueError("invalid CRK amount")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError("CRK amount must be positive")
    scaled = value * COIN
    integral = scaled.to_integral_value()
    if scaled != integral:
        raise ValueError("CRK supports at most 8 decimal places")
    atoms = int(integral)
    if atoms < 0 or (atoms == 0 and not allow_zero):
        raise ValueError("invalid CRK amount")
    return atoms


def _crk(atoms: int) -> str:
    value = Decimal(int(atoms)) / Decimal(COIN)
    return f"{value:.8f}"


def _load_wallet(label: str) -> KeyPair:
    path = WALLET_FILES.get(str(label))
    if path is None:
        raise ValueError("unknown local wallet")
    if not path.is_file():
        raise ValueError(f"wallet file not found: {label}")
    return KeyPair.load(path)


def _wallet_summaries() -> list[dict[str, Any]]:
    try:
        pool_stats = base._pool_rpc("pool.stats", timeout=5.0)
        credits = dict(pool_stats.get("balances") or {})
    except Exception:
        credits = {}

    result: list[dict[str, Any]] = []
    for label in WALLET_FILES:
        try:
            key = _load_wallet(label)
            balance = base._http_json(f"{NODE1}/pow/v2/balance/{key.address}", timeout=5.0)
            confirmed = int(balance.get("confirmed", 0))
            immature = int(balance.get("immature", 0))
            total = int(balance.get("total", confirmed + immature))
            pool_credit = int(credits.get(key.address, 0))
            result.append(
                {
                    "label": label,
                    "available": True,
                    "address": key.address,
                    "confirmed_atoms": confirmed,
                    "confirmed_crk": _crk(confirmed),
                    "immature_atoms": immature,
                    "immature_crk": _crk(immature),
                    "total_atoms": total,
                    "total_crk": _crk(total),
                    "pool_credit_atoms": pool_credit,
                    "pool_credit_crk": _crk(pool_credit),
                    "private_key_exposed": False,
                }
            )
        except Exception as exc:
            result.append({"label": label, "available": False, "error": str(exc), "private_key_exposed": False})
    return result


def _latest_blocks(limit: int) -> dict[str, Any]:
    limit = max(1, min(int(limit), 20))
    info = base._http_json(f"{NODE1}/pow/v2/info", timeout=5.0)
    tip = int(info["height"])
    start = max(0, tip - limit + 1)
    blocks: list[dict[str, Any]] = []
    for height in range(tip, start - 1, -1):
        block = base._http_json(f"{NODE1}/pow/v2/block/{height}", timeout=5.0)
        header = dict(block.get("header") or {})
        blocks.append(
            {
                "height": int(header.get("height", height)),
                "block_hash": block.get("block_hash"),
                "previous_hash": header.get("previous_hash"),
                "timestamp": header.get("timestamp"),
                "target": header.get("target"),
                "chainwork": block.get("chainwork"),
                "transaction_count": len(block.get("transactions") or []),
                "nonce": header.get("nonce"),
                "extra_nonce": header.get("extra_nonce"),
            }
        )
    return {"tip_height": tip, "blocks": blocks, "production_mainnet_ready": False}


@base.app.get("/api/v41/wallets")
def api_wallets() -> dict[str, Any]:
    return {
        "wallets": _wallet_summaries(),
        "local_only": True,
        "private_keys_returned": False,
        "production_mainnet_ready": False,
    }


@base.app.get("/api/v41/wallet/{label}/utxos")
def api_wallet_utxos(label: str) -> dict[str, Any]:
    try:
        key = _load_wallet(label)
        result = base._http_json(f"{NODE1}/pow/v2/utxos/{key.address}", timeout=5.0)
        return {
            "label": label,
            "address": key.address,
            "utxos": result.get("utxos", []),
            "production_mainnet_ready": False,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@base.app.post("/api/v41/wallet/send")
def api_wallet_send(payload: WalletSendRequest, request: Request) -> dict[str, Any]:
    if request.headers.get("x-crakbit-local-token", "") != LOCAL_WRITE_TOKEN:
        raise HTTPException(status_code=403, detail="local write token rejected")
    if not payload.to_address.startswith("crk1") or len(payload.to_address) < 20:
        raise HTTPException(status_code=400, detail="invalid destination address")

    try:
        amount = _atoms(payload.amount_crk)
        fee = _atoms(payload.fee_crk, allow_zero=True)
        key = _load_wallet(payload.wallet)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.to_address == key.address:
        raise HTTPException(status_code=400, detail="destination must differ from source wallet")

    with SEND_LOCK:
        try:
            utxo_payload = base._http_json(f"{NODE1}/pow/v2/utxos/{key.address}", timeout=5.0)
            selected: list[dict[str, Any]] = []
            total = 0
            for utxo in list(utxo_payload.get("utxos") or []):
                if not bool(utxo.get("mature")):
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
                outputs.append({"address": key.address, "amount": change})
            unsigned = build_unsigned_transaction(
                [{"txid": item["txid"], "vout": int(item["vout"])} for item in selected],
                outputs,
            )
            signed = sign_transaction(unsigned, key, selected)
            submitted = _post_json(f"{NODE1}/pow/v2/submittransaction", {"transaction": signed}, timeout=8.0)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "accepted": bool(submitted.get("accepted")),
        "txid": submitted.get("txid"),
        "fee_atoms": int(submitted.get("fee", fee)),
        "fee_crk": _crk(int(submitted.get("fee", fee))),
        "from_wallet": payload.wallet,
        "from_address": key.address,
        "to_address": payload.to_address,
        "amount_atoms": amount,
        "amount_crk": _crk(amount),
        "private_key_exposed": False,
        "local_only": True,
        "production_mainnet_ready": False,
    }


@base.app.get("/api/v41/explorer/latest")
def api_explorer_latest(limit: int = 10) -> dict[str, Any]:
    try:
        return _latest_blocks(limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@base.app.get("/api/v41/explorer/block/{height}")
def api_explorer_block(height: int) -> dict[str, Any]:
    try:
        return base._http_json(f"{NODE1}/pow/v2/block/{int(height)}", timeout=5.0)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@base.app.get("/api/v41/explorer/hash/{block_hash}")
def api_explorer_hash(block_hash: str) -> dict[str, Any]:
    if len(block_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in block_hash):
        raise HTTPException(status_code=400, detail="invalid block hash")
    try:
        return base._http_json(f"{NODE1}/pow/v2/blockhash/{block_hash.lower()}", timeout=5.0)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@base.app.get("/api/v41/explorer/mempool")
def api_explorer_mempool() -> dict[str, Any]:
    try:
        return base._http_json(f"{NODE1}/pow/v2/mempool", timeout=5.0)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


TOKEN_JSON = json.dumps(LOCAL_WRITE_TOKEN)
base.INDEX_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crakbit Chain Local Console</title>
<style>
:root{color-scheme:dark;--bg:#070b10;--panel:#101720;--panel2:#0c1219;--line:#253241;--text:#eff6ff;--muted:#8ea0b4;--ok:#43d17a;--warn:#ffc85a;--bad:#ff6576;--accent:#63a8ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#17263a 0,#080d13 35%,#070b10 70%);color:var(--text);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}.wrap{max-width:1280px;margin:auto;padding:22px}.banner{padding:12px 18px;border:1px solid #795119;background:#302311;color:#ffd78a;border-radius:12px;text-align:center;font-weight:850;letter-spacing:.1em}.top{display:flex;justify-content:space-between;gap:18px;align-items:center;margin:20px 0}.top h1{margin:0;font-size:28px}.muted{color:var(--muted)}.tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button,button{border:1px solid #34516f;background:#132b45;color:#fff;border-radius:9px;padding:9px 13px;cursor:pointer}.tabs button.active{background:#24588d}.section{display:none}.section.active{display:block}.grid{display:grid;gap:14px}.summary{grid-template-columns:repeat(4,1fr)}.nodes{grid-template-columns:repeat(4,1fr);margin-top:14px}.wallets{grid-template-columns:repeat(3,1fr)}.two{grid-template-columns:1fr 1fr}.card{background:linear-gradient(180deg,#111a25,#0d141c);border:1px solid var(--line);border-radius:14px;padding:15px;box-shadow:0 12px 30px #0004}.big{font-size:24px;font-weight:800}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.row{display:flex;justify-content:space-between;gap:12px;padding:5px 0;border-bottom:1px solid #1a2632}.row:last-child{border:0}.hash{font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-all}.addr{font:12px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-all}input,select{width:100%;margin:5px 0 11px;background:#091019;border:1px solid #2a3a4b;color:#fff;border-radius:8px;padding:10px}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:8px;border-bottom:1px solid #1c2936;text-align:left;vertical-align:top}.table th{color:var(--muted);font-weight:600}.scroll{overflow:auto}.pill{font-size:11px;border:1px solid #2d4054;border-radius:99px;padding:2px 7px}.notice{padding:10px 12px;border-radius:9px;background:#101d2a;border:1px solid #2c4257;margin:10px 0}.worker{padding:9px 0;border-bottom:1px solid #1b2632}pre{white-space:pre-wrap;word-break:break-all;background:#080d12;border:1px solid #21303e;border-radius:10px;padding:12px;max-height:480px;overflow:auto}@media(max-width:950px){.summary,.nodes,.wallets{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}}@media(max-width:560px){.summary,.nodes,.wallets{grid-template-columns:1fr}.top{align-items:flex-start;flex-direction:column}}
</style></head><body><div class="wrap">
<div class="banner">LOCAL REHEARSAL — NOT MAINNET — NO REAL-VALUE CUSTODY</div>
<div class="top"><div><h1>Crakbit Chain Console <span class="pill">v0.41</span></h1><div class="muted" id="stamp">Loading…</div></div><div class="tabs"><button class="active" data-tab="ops">Operations</button><button data-tab="wallet">Wallets</button><button data-tab="explorer">Explorer</button><button data-tab="mining">Mining</button></div></div>
<section id="ops" class="section active"><div class="grid summary" id="summary"></div><div class="grid nodes" id="nodes"></div><div class="grid two" style="margin-top:14px"><div class="card"><h3>Rehearsal Evidence</h3><div id="phase"></div><button onclick="saveEvidence()">Save Evidence Snapshot</button></div><div class="card"><h3>Scope</h3><div class="notice">Single-host Docker local rehearsal. This console does not claim public testnet, independent operator diversity, or mainnet readiness.</div><div id="scope"></div></div></div></section>
<section id="wallet" class="section"><div class="grid wallets" id="walletCards"></div><div class="grid two" style="margin-top:14px"><div class="card"><h3>Send Local CRK</h3><div class="notice">Signs inside this local dashboard process. Private keys are never returned to the browser. Pool credits are not the same as spendable on-chain balance.</div><label>Source wallet</label><select id="sendWallet"></select><label>Destination address</label><input id="sendTo" placeholder="crk1..."><label>Amount CRK</label><input id="sendAmount" value="1.00000000"><label>Fee CRK</label><input id="sendFee" value="0.00010000"><button onclick="sendCrk()">Sign & Submit Local Transaction</button><div id="sendResult" class="muted" style="margin-top:10px"></div></div><div class="card"><h3>Wallet UTXOs</h3><select id="utxoWallet" onchange="loadUtxos()"></select><div id="utxos" class="scroll"></div></div></div></section>
<section id="explorer" class="section"><div class="grid two"><div class="card"><h3>Block Lookup</h3><input id="blockQuery" placeholder="Height or 64-char block hash"><button onclick="lookupBlock()">Lookup</button><pre id="blockDetail">Enter a height or block hash.</pre></div><div class="card"><h3>Mempool</h3><div id="mempool"></div></div></div><div class="card" style="margin-top:14px"><h3>Latest Blocks</h3><div id="blocks" class="scroll"></div></div></section>
<section id="mining" class="section"><div class="grid two"><div class="card"><h3>Pool</h3><div id="pool"></div></div><div class="card"><h3>Workers</h3><div id="workers"></div></div></div><div class="notice">Mining controls are intentionally status-only in v0.41. The dashboard is not given Docker-socket/root control.</div></section>
</div><script>
const WRITE_TOKEN=__TOKEN__;
const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const row=(k,v,cls='')=>`<div class="row"><span class="muted">${esc(k)}</span><span class="${cls}">${esc(v)}</span></div>`;
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.section').forEach(s=>s.classList.toggle('active',s.id===b.dataset.tab));});
async function jget(u){const r=await fetch(u,{cache:'no-store'});if(!r.ok)throw new Error((await r.json()).detail||r.statusText);return r.json()}
async function refreshStatus(){try{const d=await jget('/api/status');document.getElementById('stamp').textContent=`${d.timestamp} • ${d.network_scope} • commit ${d.source_commit.slice(0,12)}`;const c=d.consensus;document.getElementById('summary').innerHTML=`<div class="card"><div class="muted">Nodes online</div><div class="big ${c.online_nodes===4?'ok':'bad'}">${c.online_nodes}/4</div></div><div class="card"><div class="muted">Height spread</div><div class="big ${c.height_spread<=2?'ok':'bad'}">${c.height_spread??'—'}</div></div><div class="card"><div class="muted">Strict convergence</div><div class="big ${c.strict_convergence?'ok':'warn'}">${c.strict_convergence?'YES':'LIVE'}</div></div><div class="card"><div class="muted">Alert</div><div class="big ${c.degraded_or_diverged?'bad':'ok'}">${c.degraded_or_diverged?'CHECK':'CLEAR'}</div></div>`;document.getElementById('nodes').innerHTML=Object.entries(d.nodes).map(([name,n])=>`<div class="card"><h3>${esc(name)} <span class="${n.online?'ok':'bad'}">●</span></h3>${n.online?row('Height',n.height)+row('Chainwork',n.chainwork)+row('Peers',n.peer_count)+row('RPC',n.rpc_latency_ms+' ms')+row('Side',n.side_chain_blocks)+row('Orphans',n.orphan_blocks)+`<div class="muted">Tip</div><div class="hash">${esc(n.best_block_hash)}</div>`:row('Error',n.error,'bad')}</div>`).join('');const ph=d.phase;document.getElementById('phase').innerHTML=ph?row('Phase 3',ph.rehearsal_passed?'PASS':'FAIL',ph.rehearsal_passed?'ok':'bad')+row('reorg:true',ph.reorg?'YES':'NO',ph.reorg?'ok':'bad')+row('Fork height',ph.fork_height)+row('Source DB modified',String(ph.source_database_modified),ph.source_database_modified?'bad':'ok'):'No phase3 evidence';document.getElementById('scope').innerHTML=row('Mainnet ready',String(d.claims.production_mainnet_ready),d.claims.production_mainnet_ready?'bad':'ok')+row('Production launched',String(d.claims.production_crkbit_launched),d.claims.production_crkbit_launched?'bad':'ok');document.getElementById('pool').innerHTML=d.pool.online?row('Status','ONLINE','ok')+row('Shares',d.pool.share_count)+row('Unique',d.pool.unique_submissions)+row('Workers',d.pool.workers)+row('Rounds',d.pool.rounds):row('Status','OFFLINE','bad')+row('Error',d.pool.error,'bad');document.getElementById('workers').innerHTML=d.workers.map(w=>`<div class="worker"><b>${esc(w.worker)}</b> <span class="${w.active?'ok':'warn'}">${w.active?'ACTIVE':'IDLE'}</span>${row('Shares',w.share_count)}${row('Share multiplier',w.share_multiplier)}${row('Last share',w.last_share_age_seconds==null?'—':w.last_share_age_seconds.toFixed(1)+'s ago')}</div>`).join('')}catch(e){document.getElementById('stamp').textContent='Status error: '+e.message}}
async function refreshWallets(){try{const d=await jget('/api/v41/wallets');const good=d.wallets.filter(w=>w.available);document.getElementById('walletCards').innerHTML=d.wallets.map(w=>`<div class="card"><h3>${esc(w.label)}</h3>${w.available?`<div class="addr">${esc(w.address)}</div>${row('Spendable',w.confirmed_crk+' CRK','ok')}${row('Immature',w.immature_crk+' CRK','warn')}${row('On-chain total',w.total_crk+' CRK')}${row('Pool credit',w.pool_credit_crk+' CRK')}${row('Private key exposed','NO','ok')}`:row('Error',w.error,'bad')}</div>`).join('');const options=good.map(w=>`<option value="${esc(w.label)}">${esc(w.label)} — ${esc(w.confirmed_crk)} CRK</option>`).join('');const a=document.getElementById('sendWallet'),b=document.getElementById('utxoWallet');if(a.innerHTML!==options)a.innerHTML=options;if(b.innerHTML!==options){b.innerHTML=options;loadUtxos()}}catch(e){document.getElementById('walletCards').innerHTML=`<div class="card bad">${esc(e.message)}</div>`}}
async function loadUtxos(){const w=document.getElementById('utxoWallet').value;if(!w)return;try{const d=await jget('/api/v41/wallet/'+encodeURIComponent(w)+'/utxos');document.getElementById('utxos').innerHTML=d.utxos.length?`<table class="table"><tr><th>Tx</th><th>Vout</th><th>Amount</th><th>Mature</th></tr>${d.utxos.map(u=>`<tr><td class="hash">${esc(u.txid)}</td><td>${u.vout}</td><td>${(Number(u.amount)/1e8).toFixed(8)}</td><td class="${u.mature?'ok':'warn'}">${u.mature?'YES':'NO'}</td></tr>`).join('')}</table>`:'<span class="muted">No UTXOs</span>'}catch(e){document.getElementById('utxos').textContent=e.message}}
async function sendCrk(){const wallet=document.getElementById('sendWallet').value,to_address=document.getElementById('sendTo').value.trim(),amount_crk=document.getElementById('sendAmount').value.trim(),fee_crk=document.getElementById('sendFee').value.trim();if(!confirm(`LOCAL REHEARSAL ONLY\n\nSend ${amount_crk} CRK from ${wallet} to ${to_address}?`))return;const out=document.getElementById('sendResult');out.textContent='Signing and submitting…';try{const r=await fetch('/api/v41/wallet/send',{method:'POST',headers:{'Content-Type':'application/json','X-Crakbit-Local-Token':WRITE_TOKEN},body:JSON.stringify({wallet,to_address,amount_crk,fee_crk})});const d=await r.json();if(!r.ok)throw new Error(d.detail||r.statusText);out.innerHTML=`<span class="ok">Accepted</span><div class="hash">TXID ${esc(d.txid)}</div>`;setTimeout(()=>{refreshWallets();refreshExplorer()},1500)}catch(e){out.innerHTML=`<span class="bad">${esc(e.message)}</span>`}}
async function refreshExplorer(){try{const [d,m]=await Promise.all([jget('/api/v41/explorer/latest?limit=12'),jget('/api/v41/explorer/mempool')]);document.getElementById('blocks').innerHTML=`<table class="table"><tr><th>Height</th><th>Hash</th><th>Txs</th><th>Chainwork</th></tr>${d.blocks.map(b=>`<tr><td><button onclick="showHeight(${b.height})">${b.height}</button></td><td class="hash">${esc(b.block_hash)}</td><td>${b.transaction_count}</td><td>${esc(b.chainwork)}</td></tr>`).join('')}</table>`;const txs=m.transactions||[];document.getElementById('mempool').innerHTML=row('Transactions',txs.length,txs.length?'warn':'ok')+(txs.length?txs.map(t=>`<div class="hash">${esc(t.txid)} • fee ${(Number(t.fee)/1e8).toFixed(8)} CRK</div>`).join(''):'<div class="muted">Mempool empty</div>')}catch(e){document.getElementById('blocks').textContent='Explorer error: '+e.message}}
async function showHeight(h){document.getElementById('blockQuery').value=String(h);lookupBlock();document.querySelector('[data-tab="explorer"]').click()}
async function lookupBlock(){const q=document.getElementById('blockQuery').value.trim(),out=document.getElementById('blockDetail');if(!q)return;out.textContent='Loading…';try{const url=/^\d+$/.test(q)?'/api/v41/explorer/block/'+q:/^[0-9a-fA-F]{64}$/.test(q)?'/api/v41/explorer/hash/'+q:null;if(!url)throw new Error('Enter a block height or 64-character block hash');out.textContent=JSON.stringify(await jget(url),null,2)}catch(e){out.textContent=e.message}}
async function saveEvidence(){try{const r=await fetch('/api/evidence',{method:'POST'}).then(r=>r.json());alert(r.saved?'Evidence saved: '+r.path:'Evidence save failed')}catch(e){alert(e.message)}}
refreshStatus();refreshWallets();refreshExplorer();setInterval(refreshStatus,5000);setInterval(refreshWallets,10000);setInterval(refreshExplorer,10000);
</script></body></html>'''.replace('__TOKEN__', TOKEN_JSON)

base.app.version = "0.41.0-local"


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local wallet/explorer/mining console v0.41")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=38080)
    parser.add_argument("--auto-evidence-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.auto_evidence_seconds > 0:
        thread = threading.Thread(target=base._auto_snapshot_loop, args=(args.auto_evidence_seconds,), daemon=True)
        thread.start()
    uvicorn.run(base.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
