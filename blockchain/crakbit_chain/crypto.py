from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def address_from_public_key(public_key_b64: str) -> str:
    raw = base64.b64decode(public_key_b64)
    digest = hashlib.sha256(raw).hexdigest()
    return "crk1" + digest[:40]


@dataclass(frozen=True)
class KeyPair:
    private_key_b64: str
    public_key_b64: str
    address: str

    @classmethod
    def generate(cls) -> "KeyPair":
        private = Ed25519PrivateKey.generate()
        private_raw = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        public_b64 = base64.b64encode(public_raw).decode("ascii")
        return cls(
            private_key_b64=base64.b64encode(private_raw).decode("ascii"),
            public_key_b64=public_b64,
            address=address_from_public_key(public_b64),
        )

    def sign(self, payload: bytes) -> str:
        private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(self.private_key_b64))
        return base64.b64encode(private.sign(payload)).decode("ascii")

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "private_key": self.private_key_b64,
                    "public_key": self.public_key_b64,
                    "address": self.address,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "KeyPair":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        public_key = str(data["public_key"])
        derived = address_from_public_key(public_key)
        address = str(data.get("address", derived))
        if address != derived:
            raise ValueError("key file address does not match public key")
        return cls(str(data["private_key"]), public_key, address)


def verify_signature(public_key_b64: str, payload: bytes, signature_b64: str) -> bool:
    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        public.verify(base64.b64decode(signature_b64), payload)
        return True
    except Exception:
        return False
