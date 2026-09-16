from __future__ import annotations

import argparse

from crakbit_chain.transport_security import certificate_sha256_from_pem


def main() -> int:
    parser = argparse.ArgumentParser(description="Print SHA-256 fingerprint for a PEM certificate")
    parser.add_argument("certificate")
    args = parser.parse_args()
    print(certificate_sha256_from_pem(args.certificate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
