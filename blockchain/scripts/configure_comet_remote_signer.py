from __future__ import annotations

import argparse
import ipaddress
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse


SETTING = "priv_validator_laddr"
PATTERN = re.compile(r'^(\s*priv_validator_laddr\s*=\s*)"[^"]*"(\s*(?:#.*)?)$', re.MULTILINE)


def is_loopback_tcp(address: str) -> bool:
    parsed = urlparse(address)
    if parsed.scheme != "tcp" or not parsed.hostname or parsed.port is None:
        return False
    if parsed.hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


def patch_config(text: str, signer_address: str) -> str:
    matches = list(PATTERN.finditer(text))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {SETTING} setting in CometBFT config.toml, found {len(matches)}"
        )
    return PATTERN.sub(lambda match: f'{match.group(1)}"{signer_address}"{match.group(2)}', text, count=1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Point a CometBFT validator at an operator-managed remote signer. "
            "This configures CometBFT only; it does not create, migrate or expose validator keys."
        )
    )
    parser.add_argument("--config", required=True, help="CometBFT config.toml")
    parser.add_argument("--signer", required=True, help="Remote signer address, e.g. tcp://127.0.0.1:1234")
    parser.add_argument(
        "--allow-non-loopback",
        action="store_true",
        help="Allow a non-loopback TCP signer address; use only with separately authenticated/encrypted private transport",
    )
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    if not args.signer.startswith("tcp://"):
        raise SystemExit("--signer must use a tcp:// address")
    if not args.allow_non_loopback and not is_loopback_tcp(args.signer):
        raise SystemExit(
            "non-loopback signer address refused by default; use a local signer or pass --allow-non-loopback only after securing the private signer transport"
        )

    target = Path(args.config)
    if not target.is_file():
        raise SystemExit(f"CometBFT config not found: {target}")
    original = target.read_text(encoding="utf-8")
    try:
        updated = patch_config(original, args.signer)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre-remote-signer.bak")
        if backup.exists():
            raise SystemExit(f"backup already exists; refusing to overwrite: {backup}")
        shutil.copy2(target, backup)
        print(f"backup: {backup}")

    target.write_text(updated, encoding="utf-8")
    print(f"updated {SETTING} -> {args.signer}")
    print("No validator private key was read, copied or modified by this helper.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
