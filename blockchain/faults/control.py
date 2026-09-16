from __future__ import annotations

import argparse

import httpx

API = "http://127.0.0.1:8474"
PROXIES = {
    "validator-1": ("0.0.0.0:19101", "host.docker.internal:9101"),
    "validator-2": ("0.0.0.0:19102", "host.docker.internal:9102"),
    "validator-3": ("0.0.0.0:19103", "host.docker.internal:9103"),
    "validator-4": ("0.0.0.0:19104", "host.docker.internal:9104"),
}


def setup() -> None:
    with httpx.Client(timeout=5.0) as client:
        for name, (listen, upstream) in PROXIES.items():
            response = client.post(
                f"{API}/proxies",
                json={"name": name, "listen": listen, "upstream": upstream, "enabled": True},
            )
            if response.status_code not in {200, 201, 409}:
                response.raise_for_status()


def set_enabled(name: str, enabled: bool) -> None:
    response = httpx.post(f"{API}/proxies/{name}", json={"enabled": enabled}, timeout=5.0)
    response.raise_for_status()


def clear_toxics(name: str) -> None:
    response = httpx.get(f"{API}/proxies/{name}/toxics", timeout=5.0)
    response.raise_for_status()
    for toxic in response.json():
        httpx.delete(f"{API}/proxies/{name}/toxics/{toxic['name']}", timeout=5.0).raise_for_status()


def add_latency(name: str, latency_ms: int, jitter_ms: int) -> None:
    clear_toxics(name)
    response = httpx.post(
        f"{API}/proxies/{name}/toxics",
        json={
            "name": "latency",
            "type": "latency",
            "stream": "downstream",
            "toxicity": 1.0,
            "attributes": {"latency": latency_ms, "jitter": jitter_ms},
        },
        timeout=5.0,
    )
    response.raise_for_status()


def add_timeout(name: str, timeout_ms: int) -> None:
    clear_toxics(name)
    response = httpx.post(
        f"{API}/proxies/{name}/toxics",
        json={
            "name": "timeout",
            "type": "timeout",
            "stream": "downstream",
            "toxicity": 1.0,
            "attributes": {"timeout": timeout_ms},
        },
        timeout=5.0,
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Crakbit devnet transport fault controller")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup")
    reset = sub.add_parser("reset")
    reset.add_argument("proxy", choices=sorted(PROXIES))
    down = sub.add_parser("down")
    down.add_argument("proxy", choices=sorted(PROXIES))
    up = sub.add_parser("up")
    up.add_argument("proxy", choices=sorted(PROXIES))
    latency = sub.add_parser("latency")
    latency.add_argument("proxy", choices=sorted(PROXIES))
    latency.add_argument("--ms", type=int, required=True)
    latency.add_argument("--jitter", type=int, default=0)
    timeout = sub.add_parser("timeout")
    timeout.add_argument("proxy", choices=sorted(PROXIES))
    timeout.add_argument("--ms", type=int, required=True)

    args = parser.parse_args()
    if args.command == "setup":
        setup()
    elif args.command == "reset":
        clear_toxics(args.proxy)
        set_enabled(args.proxy, True)
    elif args.command == "down":
        set_enabled(args.proxy, False)
    elif args.command == "up":
        set_enabled(args.proxy, True)
    elif args.command == "latency":
        add_latency(args.proxy, args.ms, args.jitter)
    elif args.command == "timeout":
        add_timeout(args.proxy, args.ms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
