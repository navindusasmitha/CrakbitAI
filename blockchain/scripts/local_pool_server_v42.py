from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import time

from crakbit_chain.pow_pool_v31 import PoolConfig
from crakbit_chain.pow_pool_v33 import (
    HardenedCrakbitPool,
    HardenedPoolLedger,
    PoolSessionV33,
    VardiffPolicy,
)


async def run_server(
    pool: HardenedCrakbitPool,
    *,
    host: str,
    port: int,
    max_messages_per_second: int,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    auth_token: str | None = None,
    max_line_bytes: int = 64 * 1024,
) -> None:
    if bool(tls_cert) != bool(tls_key):
        raise ValueError("TLS certificate and key must be provided together")

    ssl_context: ssl.SSLContext | None = None
    if tls_cert and tls_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.load_cert_chain(tls_cert, tls_key)

    max_messages_per_second = max(1, min(int(max_messages_per_second), 1000))
    max_line_bytes = max(1024, min(int(max_line_bytes), 1_000_000))

    async def client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        session = PoolSessionV33(pool, auth_token=auth_token)
        window_second = int(time.time())
        count = 0
        try:
            while not reader.at_eof():
                raw = await reader.readline()
                if not raw:
                    break
                if len(raw) > max_line_bytes:
                    break

                current = int(time.time())
                if current != window_second:
                    window_second = current
                    count = 0
                count += 1
                if count > max_messages_per_second:
                    response = {"id": None, "result": None, "error": "pool connection rate limit exceeded"}
                    writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                    try:
                        await writer.drain()
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        pass
                    break

                try:
                    request = json.loads(raw.decode("utf-8"))
                    if not isinstance(request, dict):
                        raise ValueError("request must be a JSON object")
                    response = session.handle(request)
                except Exception as exc:
                    response = {"id": None, "result": None, "error": str(exc)}

                writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                try:
                    await writer.drain()
                except (ConnectionResetError, BrokenPipeError, OSError):
                    break
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                return
            try:
                await writer.wait_closed()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass

    server = await asyncio.start_server(client_connected, host=host, port=int(port), ssl=ssl_context)
    async with server:
        await server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Crakbit local pool server with graceful disconnect handling")
    parser.add_argument("--db", required=True)
    parser.add_argument("--node-url", default="http://127.0.0.1:28443")
    parser.add_argument("--pool-address", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3333)
    parser.add_argument("--pplns-window-shares", type=int, default=1000)
    parser.add_argument("--initial-share-multiplier", type=int, default=256)
    parser.add_argument("--minimum-share-multiplier", type=int, default=4)
    parser.add_argument("--maximum-share-multiplier", type=int, default=1048576)
    parser.add_argument("--vardiff-target-seconds", type=float, default=15.0)
    parser.add_argument("--vardiff-retarget-shares", type=int, default=8)
    parser.add_argument("--stale-job-seconds", type=int, default=120)
    parser.add_argument("--tls-cert", default=None)
    parser.add_argument("--tls-key", default=None)
    parser.add_argument("--auth-token", default=None)
    parser.add_argument("--max-messages-per-second", type=int, default=100)
    args = parser.parse_args()

    ledger = HardenedPoolLedger(args.db)
    vardiff = VardiffPolicy(
        target_share_seconds=args.vardiff_target_seconds,
        minimum_multiplier=args.minimum_share_multiplier,
        maximum_multiplier=args.maximum_share_multiplier,
        initial_multiplier=args.initial_share_multiplier,
        retarget_every_shares=args.vardiff_retarget_shares,
    )
    pool = HardenedCrakbitPool(
        PoolConfig(
            node_url=args.node_url,
            pool_address=args.pool_address,
            share_target_multiplier=args.initial_share_multiplier,
            pplns_window_shares=args.pplns_window_shares,
        ),
        ledger,
        vardiff=vardiff,
        stale_job_seconds=args.stale_job_seconds,
    )

    print(json.dumps({
        "pool_protocol": "crakbit-pool/2",
        "listen": f"{args.host}:{args.port}",
        "node_url": args.node_url,
        "graceful_disconnect_cleanup": True,
        "local_rehearsal": True,
        "production_mainnet_ready": False,
    }))

    try:
        asyncio.run(run_server(
            pool,
            host=args.host,
            port=args.port,
            tls_cert=args.tls_cert,
            tls_key=args.tls_key,
            auth_token=args.auth_token,
            max_messages_per_second=args.max_messages_per_second,
        ))
    finally:
        ledger.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
