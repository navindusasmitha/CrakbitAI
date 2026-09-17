from __future__ import annotations

import argparse
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

NODE_URLS = {
    "node1": os.environ.get("CRAKBIT_NODE1_URL", "http://node1:28443"),
    "node2": os.environ.get("CRAKBIT_NODE2_URL", "http://node2:28443"),
    "node3": os.environ.get("CRAKBIT_NODE3_URL", "http://node3:28443"),
    "node4": os.environ.get("CRAKBIT_NODE4_URL", "http://node4:28443"),
}
POOL_HOST = os.environ.get("CRAKBIT_POOL_HOST", "pool")
POOL_PORT = int(os.environ.get("CRAKBIT_POOL_PORT", "3333"))
POOL_DB = Path(os.environ.get("CRAKBIT_POOL_DB", "/runtime/pool/pool.sqlite3"))
EVIDENCE_DIR = Path(os.environ.get("CRAKBIT_EVIDENCE_DIR", "/evidence"))
SOURCE_COMMIT = os.environ.get("CRAKBIT_SOURCE_COMMIT", "unknown")
BANNER = "LOCAL REHEARSAL — NOT MAINNET"

app = FastAPI(title="Crakbit Local Rehearsal Dashboard", version="0.39.0-local")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_json(url: str, timeout: float = 2.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _pool_rpc(method: str, timeout: float = 2.0) -> dict[str, Any]:
    import socket

    payload = json.dumps({"id": 1, "method": method, "params": {}}, separators=(",", ":")) + "\n"
    with socket.create_connection((POOL_HOST, POOL_PORT), timeout=timeout) as sock:
        sock.sendall(payload.encode("utf-8"))
        sock.settimeout(timeout)
        data = b""
        while not data.endswith(b"\n"):
            part = sock.recv(65536)
            if not part:
                break
            data += part
    if not data:
        raise RuntimeError("pool returned no response")
    response = json.loads(data.decode("utf-8").strip())
    if response.get("error"):
        raise RuntimeError(str(response["error"]))
    return dict(response.get("result") or {})


def _worker_activity() -> list[dict[str, Any]]:
    if not POOL_DB.is_file():
        return []
    uri = f"file:{POOL_DB.as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=2.0)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute(
            """
            SELECT payout_address,worker,multiplier,last_share_ms,share_count,ewma_interval_ms
            FROM worker_vardiff_v33
            ORDER BY worker
            """
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        db.close()
    now_ms = int(time.time() * 1000)
    result: list[dict[str, Any]] = []
    for row in rows:
        last_share_ms = None if row["last_share_ms"] is None else int(row["last_share_ms"])
        age_seconds = None if last_share_ms is None else max(0.0, (now_ms - last_share_ms) / 1000.0)
        result.append(
            {
                "worker": str(row["worker"]),
                "payout_address": str(row["payout_address"]),
                "share_multiplier": int(row["multiplier"]),
                "share_count": int(row["share_count"]),
                "ewma_interval_ms": None if row["ewma_interval_ms"] is None else float(row["ewma_interval_ms"]),
                "last_share_ms": last_share_ms,
                "last_share_age_seconds": age_seconds,
                "active": age_seconds is not None and age_seconds <= 120.0,
            }
        )
    return result


def _phase3_summary() -> dict[str, Any] | None:
    path = EVIDENCE_DIR / "phase3-reorg.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"present": True, "valid_json": False}
    return {
        "present": True,
        "valid_json": True,
        "rehearsal_passed": bool(data.get("rehearsal_passed")),
        "rehearsal_id": data.get("rehearsal_id"),
        "reorg": bool((data.get("reorg_result") or {}).get("reorg")),
        "fork_height": (data.get("reorg_result") or {}).get("fork_height"),
        "source_database_modified": data.get("source_database_modified"),
    }


def collect_status() -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    for name, base in NODE_URLS.items():
        try:
            info = _http_json(base.rstrip("/") + "/pow/v2/info")
            nodes[name] = {"online": True, **info}
        except Exception as exc:
            nodes[name] = {"online": False, "error": str(exc)}

    online = [value for value in nodes.values() if value.get("online")]
    heights = [int(value["height"]) for value in online if "height" in value]
    tips = {str(value.get("best_block_hash")) for value in online if value.get("best_block_hash")}
    works = {str(value.get("chainwork")) for value in online if value.get("chainwork")}
    chain_ids = {str(value.get("chain_id")) for value in online if value.get("chain_id")}
    height_spread = (max(heights) - min(heights)) if heights else None
    strict_convergence = len(online) == 4 and len(heights) == 4 and len(set(heights)) == 1 and len(tips) == 1 and len(works) == 1
    degraded = len(online) < 4 or (height_spread is not None and height_spread > 2) or len(chain_ids) > 1

    try:
        pool_stats = {"online": True, **_pool_rpc("pool.stats")}
    except Exception as exc:
        pool_stats = {"online": False, "error": str(exc)}

    workers = _worker_activity()
    active_workers = sum(1 for item in workers if item.get("active"))

    return {
        "format": "crakbit-local-dashboard-v39/1",
        "timestamp": _now_iso(),
        "banner": BANNER,
        "source_commit": SOURCE_COMMIT,
        "network_scope": "single-host Docker local rehearsal",
        "claims": {
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
            "independent_operator_diversity_verified": False,
            "independent_provider_diversity_verified": False,
            "independent_region_diversity_verified": False,
        },
        "nodes": nodes,
        "consensus": {
            "online_nodes": len(online),
            "height_spread": height_spread,
            "strict_convergence": strict_convergence,
            "degraded_or_diverged": degraded,
        },
        "pool": pool_stats,
        "workers": workers,
        "active_workers": active_workers,
        "phase3": _phase3_summary(),
    }


def save_snapshot() -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    status = collect_status()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = EVIDENCE_DIR / f"dashboard-snapshot-{stamp}.json"
    path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest = EVIDENCE_DIR / "dashboard-latest.json"
    latest.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    snapshots = sorted(EVIDENCE_DIR.glob("dashboard-snapshot-*.json"))
    for stale in snapshots[:-288]:
        try:
            stale.unlink()
        except OSError:
            pass
    return path


def _auto_snapshot_loop(interval: int) -> None:
    while True:
        try:
            save_snapshot()
        except Exception:
            pass
        time.sleep(max(60, interval))


@app.get("/api/status")
def api_status() -> JSONResponse:
    return JSONResponse(collect_status())


@app.post("/api/evidence")
def api_evidence() -> JSONResponse:
    path = save_snapshot()
    return JSONResponse({"saved": True, "path": str(path), "production_mainnet_ready": False})


@app.get("/api/evidence/latest")
def api_evidence_latest() -> JSONResponse:
    latest = EVIDENCE_DIR / "dashboard-latest.json"
    if not latest.is_file():
        return JSONResponse({"present": False, "production_mainnet_ready": False})
    return JSONResponse({"present": True, "snapshot": json.loads(latest.read_text(encoding="utf-8"))})


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crakbit Local Rehearsal</title>
<style>
:root{color-scheme:dark;--bg:#090d12;--panel:#111821;--line:#263241;--text:#eef4fb;--muted:#96a5b5;--ok:#43d17a;--warn:#ffca58;--bad:#ff6678;--accent:#68a7ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#172131 0,#090d12 45%);color:var(--text);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}.wrap{max-width:1180px;margin:auto;padding:24px}.banner{padding:13px 18px;border:1px solid #754d19;background:#2c2110;border-radius:12px;color:#ffd98a;font-weight:800;letter-spacing:.08em;text-align:center}.head{display:flex;justify-content:space-between;align-items:center;gap:16px;margin:24px 0}.head h1{margin:0;font-size:28px}.muted{color:var(--muted)}button{border:1px solid #36567b;background:#163558;color:#fff;border-radius:9px;padding:9px 13px;cursor:pointer}.summary,.nodes,.bottom{display:grid;gap:14px}.summary{grid-template-columns:repeat(4,1fr);margin-bottom:14px}.nodes{grid-template-columns:repeat(4,1fr)}.bottom{grid-template-columns:1fr 1fr;margin-top:14px}.card{background:linear-gradient(180deg,#131b25,#0f151d);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:0 12px 30px #0004}.big{font-size:24px;font-weight:750}.row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid #1b2632}.row:last-child{border:0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.hash{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px;word-break:break-all}.worker{padding:9px 0;border-bottom:1px solid #1b2632}@media(max-width:900px){.summary,.nodes{grid-template-columns:1fr 1fr}.bottom{grid-template-columns:1fr}}@media(max-width:520px){.summary,.nodes{grid-template-columns:1fr}.head{align-items:flex-start;flex-direction:column}}
</style>
</head><body><div class="wrap">
<div class="banner">LOCAL REHEARSAL — NOT MAINNET</div>
<div class="head"><div><h1>Crakbit Chain Operations</h1><div class="muted" id="stamp">Loading…</div></div><button onclick="saveEvidence()">Save Evidence Snapshot</button></div>
<div class="summary" id="summary"></div><div class="nodes" id="nodes"></div><div class="bottom"><div class="card"><h3>Pool & Workers</h3><div id="pool"></div></div><div class="card"><h3>Rehearsal Evidence</h3><div id="phase"></div></div></div>
</div><script>
const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function row(k,v,cls=''){return `<div class="row"><span class="muted">${esc(k)}</span><span class="${cls}">${esc(v)}</span></div>`}
async function refresh(){try{const d=await fetch('/api/status',{cache:'no-store'}).then(r=>r.json());document.getElementById('stamp').textContent=`${d.timestamp} • ${d.network_scope}`;const c=d.consensus;document.getElementById('summary').innerHTML=`<div class="card"><div class="muted">Nodes online</div><div class="big ${c.online_nodes===4?'ok':'bad'}">${c.online_nodes}/4</div></div><div class="card"><div class="muted">Height spread</div><div class="big ${c.height_spread<=2?'ok':'bad'}">${c.height_spread??'—'}</div></div><div class="card"><div class="muted">Strict convergence</div><div class="big ${c.strict_convergence?'ok':'warn'}">${c.strict_convergence?'YES':'LIVE'}</div></div><div class="card"><div class="muted">Alert</div><div class="big ${c.degraded_or_diverged?'bad':'ok'}">${c.degraded_or_diverged?'CHECK':'CLEAR'}</div></div>`;document.getElementById('nodes').innerHTML=Object.entries(d.nodes).map(([name,n])=>`<div class="card"><h3>${name} <span class="${n.online?'ok':'bad'}">${n.online?'●':'●'}</span></h3>${n.online?row('Height',n.height)+row('Chainwork',n.chainwork)+row('Peers',n.peer_count)+row('Side blocks',n.side_chain_blocks)+row('Orphans',n.orphan_blocks)+`<div class="muted">Tip</div><div class="hash">${esc(n.best_block_hash)}</div>`:row('Error',n.error,'bad')}</div>`).join('');let p=d.pool.online?row('Pool','ONLINE','ok')+row('Shares',d.pool.share_count)+row('Unique submissions',d.pool.unique_submissions)+row('Workers',d.pool.workers)+row('Rounds',d.pool.rounds):row('Pool','OFFLINE','bad')+row('Error',d.pool.error,'bad');p+=`<h4>Worker activity</h4>`+(d.workers.length?d.workers.map(w=>`<div class="worker"><b>${esc(w.worker)}</b> <span class="${w.active?'ok':'warn'}">${w.active?'ACTIVE':'IDLE'}</span><br><span class="muted">shares ${w.share_count} • multiplier ${w.share_multiplier} • last ${w.last_share_age_seconds==null?'—':w.last_share_age_seconds.toFixed(1)+'s'} ago</span></div>`).join(''):'<span class="muted">No worker rows yet</span>');document.getElementById('pool').innerHTML=p;const ph=d.phase;document.getElementById('phase').innerHTML=ph?row('Phase 3',ph.rehearsal_passed?'PASS':'FAIL',ph.rehearsal_passed?'ok':'bad')+row('reorg:true',ph.reorg?'YES':'NO',ph.reorg?'ok':'bad')+row('Fork height',ph.fork_height)+row('Source DB modified',String(ph.source_database_modified),ph.source_database_modified?'bad':'ok')+`<div class="muted">Rehearsal ID</div><div class="hash">${esc(ph.rehearsal_id)}</div>`:'<span class="muted">phase3-reorg.json not found</span>';}catch(e){document.getElementById('stamp').textContent='Dashboard API unavailable: '+e}}
async function saveEvidence(){const r=await fetch('/api/evidence',{method:'POST'}).then(r=>r.json());alert(r.saved?'Evidence saved: '+r.path:'Evidence save failed')}
refresh();setInterval(refresh,5000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local-only rehearsal dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=38080)
    parser.add_argument("--auto-evidence-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.auto_evidence_seconds > 0:
        thread = threading.Thread(target=_auto_snapshot_loop, args=(args.auto_evidence_seconds,), daemon=True)
        thread.start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
