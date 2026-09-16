from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .crypto import canonical_json

RANDOMX_UPSTREAM_TAG = "v1.1.8"
RANDOMX_ALGO_CANDIDATE = "crakpow-randomx-v1-candidate"
RANDOMX_HASH_SIZE = 32
RANDOMX_KEY_INTERVAL = 2048
RANDOMX_KEY_DELAY = 64
XMRIG_NONCE_OFFSET = 39
XMRIG_NONCE_SIZE = 4

RANDOMX_FLAG_DEFAULT = 0
RANDOMX_FLAG_LARGE_PAGES = 1
RANDOMX_FLAG_HARD_AES = 2
RANDOMX_FLAG_FULL_MEM = 4
RANDOMX_FLAG_JIT = 8
RANDOMX_FLAG_SECURE = 16
RANDOMX_FLAG_ARGON2_SSSE3 = 32
RANDOMX_FLAG_ARGON2_AVX2 = 64
RANDOMX_FLAG_ARGON2 = 96

OFFICIAL_EXAMPLE_KEY = b"RandomX example key\0"
OFFICIAL_EXAMPLE_INPUT = b"RandomX example input\0"
OFFICIAL_EXAMPLE_HASH_HEX = "8a48e5f9db45ab79d9080574c4d81954fe6ac63842214aff73c244b26330b7c9"


class RandomXV33Error(RuntimeError):
    pass


def randomx_key_height(height: int, *, interval: int = RANDOMX_KEY_INTERVAL, delay: int = RANDOMX_KEY_DELAY) -> int:
    """Return the deterministic key-block height for the v0.33 RandomX candidate.

    This follows the upstream recommendation pattern: key blocks are interval-aligned
    and a delayed activation avoids making the key miner-selectable at the activation
    height. It is candidate policy only; it is not activated in Crakbit consensus yet.
    """

    height = int(height)
    interval = int(interval)
    delay = int(delay)
    if height < 0 or interval <= 0 or delay < 0 or delay >= interval:
        raise RandomXV33Error("invalid RandomX key schedule")
    if height < delay:
        return 0
    return ((height - delay) // interval) * interval


def randomx_key_from_block_hash(block_hash_hex: str) -> bytes:
    try:
        raw = bytes.fromhex(str(block_hash_hex).strip())
    except ValueError as exc:
        raise RandomXV33Error("RandomX key block hash must be hexadecimal") from exc
    if len(raw) != 32:
        raise RandomXV33Error("RandomX key block hash must be 32 bytes")
    return raw


def randomx_candidate_blob(header: dict[str, Any]) -> bytes:
    """Build a fixed-layout RandomX candidate blob with XMRig's default nonce offset.

    The first 39 bytes commit to every header field except nonce. Bytes 39..42 are
    the little-endian 32-bit nonce expected by the common XMRig RandomX job path.
    The remaining bytes add a second independent commitment to the same header body.
    This format is an interoperability candidate and is not active consensus format.
    """

    body = dict(header)
    nonce = int(body.pop("nonce", 0))
    if nonce < 0 or nonce > 0xFFFFFFFF:
        raise RandomXV33Error("RandomX candidate nonce must fit uint32")
    encoded = canonical_json(body)
    prefix = b"CRK-RX1" + hashlib.sha256(b"crakbit-randomx-v1:" + encoded).digest()
    if len(prefix) != XMRIG_NONCE_OFFSET:
        raise RandomXV33Error("internal RandomX candidate blob layout error")
    suffix = hashlib.blake2s(encoded, digest_size=32).digest()
    return prefix + nonce.to_bytes(4, "little") + suffix


def xmrig_target_from_difficulty(difficulty: float) -> str:
    difficulty = float(difficulty)
    if difficulty <= 0:
        raise RandomXV33Error("difficulty must be positive")
    target = int(((1 << 64) - 1) / difficulty)
    target = max(1, min((1 << 64) - 1, target))
    return target.to_bytes(8, "little").hex()


def xmrig_target_from_full_target(target_256: int) -> str:
    target_256 = int(target_256)
    if target_256 <= 0 or target_256 >= 1 << 256:
        raise RandomXV33Error("256-bit target out of range")
    difficulty = ((1 << 256) - 1) / target_256
    return xmrig_target_from_difficulty(difficulty)


def _candidate_paths(explicit: str | Path | None) -> list[str]:
    values: list[str] = []
    if explicit:
        values.append(str(explicit))
    if os.environ.get("CRAKBIT_RANDOMX_LIBRARY"):
        values.append(os.environ["CRAKBIT_RANDOMX_LIBRARY"])
    found = ctypes.util.find_library("randomx")
    if found:
        values.append(found)
    values.extend([
        "randomx.dll",
        "librandomx.so",
        "librandomx.dylib",
        "vendor/RandomX-v1.1.8/build/randomx.dll",
        "vendor/RandomX-v1.1.8/build/librandomx.so",
        "vendor/RandomX-v1.1.8/build/librandomx.dylib",
        "vendor/RandomX-v1.1.8/build/Release/randomx.dll",
    ])
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def discover_randomx_library(explicit: str | Path | None = None) -> str | None:
    for candidate in _candidate_paths(explicit):
        path = Path(candidate)
        if path.is_absolute() or path.parent != Path("."):
            if not path.exists():
                continue
            return str(path.resolve())
        try:
            lib = ctypes.CDLL(candidate)
            del lib
            return candidate
        except OSError:
            continue
    return None


class _Bindings:
    def __init__(self, library_path: str):
        try:
            self.lib = ctypes.CDLL(library_path)
        except OSError as exc:
            raise RandomXV33Error(f"unable to load RandomX library: {library_path}") from exc

        self.lib.randomx_get_flags.argtypes = []
        self.lib.randomx_get_flags.restype = ctypes.c_uint32

        self.lib.randomx_alloc_cache.argtypes = [ctypes.c_uint32]
        self.lib.randomx_alloc_cache.restype = ctypes.c_void_p
        self.lib.randomx_init_cache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        self.lib.randomx_init_cache.restype = None
        self.lib.randomx_release_cache.argtypes = [ctypes.c_void_p]
        self.lib.randomx_release_cache.restype = None

        self.lib.randomx_alloc_dataset.argtypes = [ctypes.c_uint32]
        self.lib.randomx_alloc_dataset.restype = ctypes.c_void_p
        self.lib.randomx_dataset_item_count.argtypes = []
        self.lib.randomx_dataset_item_count.restype = ctypes.c_ulong
        self.lib.randomx_init_dataset.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong]
        self.lib.randomx_init_dataset.restype = None
        self.lib.randomx_release_dataset.argtypes = [ctypes.c_void_p]
        self.lib.randomx_release_dataset.restype = None

        self.lib.randomx_create_vm.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
        self.lib.randomx_create_vm.restype = ctypes.c_void_p
        self.lib.randomx_destroy_vm.argtypes = [ctypes.c_void_p]
        self.lib.randomx_destroy_vm.restype = None
        self.lib.randomx_calculate_hash.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
        self.lib.randomx_calculate_hash.restype = None


@dataclass
class RandomXRuntimeInfo:
    available: bool
    library_path: str | None
    upstream_tag: str = RANDOMX_UPSTREAM_TAG
    algorithm: str = RANDOMX_ALGO_CANDIDATE
    consensus_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "library_path": self.library_path,
            "upstream_tag": self.upstream_tag,
            "algorithm": self.algorithm,
            "consensus_enabled": self.consensus_enabled,
            "production_mainnet_ready": False,
        }


def randomx_runtime_info(explicit: str | Path | None = None) -> RandomXRuntimeInfo:
    path = discover_randomx_library(explicit)
    return RandomXRuntimeInfo(available=path is not None, library_path=path)


class RandomXContext:
    """Small ctypes owner for upstream RandomX light or fast mode.

    Fast mode allocates the full dataset (~2 GiB upstream). Light mode uses the
    cache (~256 MiB) and is intentionally the default for validation tooling.
    """

    def __init__(
        self,
        key: bytes,
        *,
        library_path: str | Path | None = None,
        mode: str = "light",
        large_pages: bool = False,
        secure_jit: bool = False,
    ):
        if not key or len(key) > 60:
            raise RandomXV33Error("RandomX key must contain 1..60 bytes")
        path = discover_randomx_library(library_path)
        if path is None:
            raise RandomXV33Error(
                "native RandomX library not found; build pinned upstream v1.1.8 and set CRAKBIT_RANDOMX_LIBRARY"
            )
        mode = str(mode).lower()
        if mode not in {"light", "fast"}:
            raise RandomXV33Error("RandomX mode must be light or fast")
        self.library_path = path
        self.mode = mode
        self.bindings = _Bindings(path)
        flags = int(self.bindings.lib.randomx_get_flags())
        if large_pages:
            flags |= RANDOMX_FLAG_LARGE_PAGES
        if secure_jit and flags & RANDOMX_FLAG_JIT:
            flags |= RANDOMX_FLAG_SECURE
        flags &= ~RANDOMX_FLAG_FULL_MEM
        self.flags = flags
        self.cache: int | None = None
        self.dataset: int | None = None
        self.vm: int | None = None

        cache_flags = flags & (RANDOMX_FLAG_LARGE_PAGES | RANDOMX_FLAG_JIT | RANDOMX_FLAG_ARGON2)
        self.cache = int(self.bindings.lib.randomx_alloc_cache(cache_flags) or 0)
        if not self.cache:
            raise RandomXV33Error("RandomX cache allocation failed")
        key_buf = ctypes.create_string_buffer(key, len(key))
        self.bindings.lib.randomx_init_cache(self.cache, ctypes.cast(key_buf, ctypes.c_void_p), len(key))

        if mode == "fast":
            dataset_flags = RANDOMX_FLAG_LARGE_PAGES if large_pages else RANDOMX_FLAG_DEFAULT
            self.dataset = int(self.bindings.lib.randomx_alloc_dataset(dataset_flags) or 0)
            if not self.dataset:
                self.close()
                raise RandomXV33Error("RandomX dataset allocation failed")
            count = int(self.bindings.lib.randomx_dataset_item_count())
            self.bindings.lib.randomx_init_dataset(self.dataset, self.cache, 0, count)
            vm_flags = flags | RANDOMX_FLAG_FULL_MEM
            self.vm = int(self.bindings.lib.randomx_create_vm(vm_flags, None, self.dataset) or 0)
        else:
            self.vm = int(self.bindings.lib.randomx_create_vm(flags, self.cache, None) or 0)
        if not self.vm:
            self.close()
            raise RandomXV33Error("RandomX VM creation failed")

    def hash(self, data: bytes) -> bytes:
        if not self.vm:
            raise RandomXV33Error("RandomX context is closed")
        data = bytes(data)
        if not data:
            raise RandomXV33Error("RandomX input may not be empty")
        input_buf = ctypes.create_string_buffer(data, len(data))
        output = (ctypes.c_ubyte * RANDOMX_HASH_SIZE)()
        self.bindings.lib.randomx_calculate_hash(
            self.vm,
            ctypes.cast(input_buf, ctypes.c_void_p),
            len(data),
            ctypes.cast(output, ctypes.c_void_p),
        )
        return bytes(output)

    def close(self) -> None:
        if getattr(self, "vm", None):
            self.bindings.lib.randomx_destroy_vm(self.vm)
            self.vm = None
        if getattr(self, "dataset", None):
            self.bindings.lib.randomx_release_dataset(self.dataset)
            self.dataset = None
        if getattr(self, "cache", None):
            self.bindings.lib.randomx_release_cache(self.cache)
            self.cache = None

    def __enter__(self) -> "RandomXContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def randomx_selftest(*, library_path: str | Path | None = None, mode: str = "light") -> dict[str, Any]:
    with RandomXContext(OFFICIAL_EXAMPLE_KEY, library_path=library_path, mode=mode) as ctx:
        digest = ctx.hash(OFFICIAL_EXAMPLE_INPUT).hex()
        passed = digest == OFFICIAL_EXAMPLE_HASH_HEX
        return {
            "passed": passed,
            "mode": mode,
            "library_path": ctx.library_path,
            "upstream_tag": RANDOMX_UPSTREAM_TAG,
            "expected": OFFICIAL_EXAMPLE_HASH_HEX,
            "actual": digest,
            "consensus_enabled": False,
            "production_mainnet_ready": False,
        }


def benchmark_randomx(
    *,
    library_path: str | Path | None = None,
    mode: str = "light",
    seconds: float = 3.0,
    key: bytes = b"Crakbit RandomX v0.33 benchmark",
) -> dict[str, Any]:
    seconds = max(0.25, min(float(seconds), 120.0))
    header = {
        "version": 1,
        "chain_id": "crakbit-randomx-candidate",
        "height": 2112,
        "previous_hash": "11" * 32,
        "merkle_root": "22" * 32,
        "timestamp": 1_800_000_000,
        "target": "00ff" + "ff" * 30,
        "pow_algo": RANDOMX_ALGO_CANDIDATE,
        "pow_seed": "33" * 32,
        "extra_nonce": 0,
        "nonce": 0,
    }
    started = time.perf_counter()
    hashes = 0
    last = b""
    with RandomXContext(key, library_path=library_path, mode=mode) as ctx:
        while time.perf_counter() - started < seconds:
            header["nonce"] = hashes & 0xFFFFFFFF
            last = ctx.hash(randomx_candidate_blob(header))
            hashes += 1
        elapsed = max(1e-9, time.perf_counter() - started)
        return {
            "algorithm": RANDOMX_ALGO_CANDIDATE,
            "upstream_tag": RANDOMX_UPSTREAM_TAG,
            "mode": mode,
            "hashes": hashes,
            "elapsed_seconds": elapsed,
            "hashrate_hps": hashes / elapsed,
            "last_hash": last.hex(),
            "library_path": ctx.library_path,
            "consensus_enabled": False,
            "production_mainnet_ready": False,
        }


def candidate_vectors() -> dict[str, Any]:
    header = {
        "version": 1,
        "chain_id": "crakbit-randomx-candidate",
        "height": 2112,
        "previous_hash": "11" * 32,
        "merkle_root": "22" * 32,
        "timestamp": 1_800_000_000,
        "target": "00ff" + "ff" * 30,
        "pow_algo": RANDOMX_ALGO_CANDIDATE,
        "pow_seed": "33" * 32,
        "extra_nonce": 7,
        "nonce": 42,
    }
    return {
        "format": "crakbit-randomx-v33-vectors/1",
        "upstream_randomx_tag": RANDOMX_UPSTREAM_TAG,
        "candidate_algorithm": RANDOMX_ALGO_CANDIDATE,
        "key_interval": RANDOMX_KEY_INTERVAL,
        "key_delay": RANDOMX_KEY_DELAY,
        "xmrig_nonce_offset": XMRIG_NONCE_OFFSET,
        "xmrig_nonce_size": XMRIG_NONCE_SIZE,
        "example_key_height": randomx_key_height(header["height"]),
        "header": header,
        "candidate_blob_hex": randomx_candidate_blob(header).hex(),
        "official_upstream_selftest": {
            "key_hex": OFFICIAL_EXAMPLE_KEY.hex(),
            "input_hex": OFFICIAL_EXAMPLE_INPUT.hex(),
            "hash_hex": OFFICIAL_EXAMPLE_HASH_HEX,
        },
        "consensus_enabled": False,
        "production_mainnet_ready": False,
    }
