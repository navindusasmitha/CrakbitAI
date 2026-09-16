# Crakbit Chain Public-Testnet Operator Scaffold

This directory contains **examples for a future research/public testnet**, not a production mainnet deployment.

The current chain remains a research devnet. Do not use it for real-value custody.

## Files

- `docker-compose.yml` — one-validator-per-host container scaffold.
- `.env.example` — RPC/resource bounds, mTLS and optional monitoring-auth variables.
- `nginx.conf.example` — reverse-proxy hardening example.
- `nftables.example.conf` — deny-by-default host firewall example.

## Minimum operator model

Each validator should run on an independent host or failure domain with:

1. a dedicated consensus Ed25519 key,
2. a separate TLS private key/certificate,
3. a validator CA trusted by all validator operators,
4. `https://` validator peer URLs with correct SANs,
5. peer certificate fingerprints distributed out-of-band,
6. the validator-internal listener restricted at firewall/VPC level,
7. a public reverse proxy separate from validator-internal traffic,
8. backups/snapshots stored outside the node filesystem,
9. monitoring reachable only from operator networks or authenticated paths,
10. documented key/certificate rotation and incident response.

## Certificate rotation

v0.12 allows a maximum of two accepted SHA-256 leaf-certificate fingerprints for one validator during a controlled rotation window:

```json
{
  "crk1VALIDATOR": [
    "old_certificate_fingerprint",
    "new_certificate_fingerprint"
  ]
}
```

Recommended sequence:

1. issue the new certificate,
2. distribute a pin file containing old + new fingerprints,
3. wait until all peers have loaded the overlap set,
4. rotate the validator certificate/key,
5. verify `/transport/status` and peer health,
6. remove the old fingerprint from all peers.

This is operator-coordinated rotation, not an automatic PKI controller.

## Monitoring authentication

A long bearer token can protect sensitive operator endpoints:

```text
CRAKBIT_MONITORING_BEARER_TOKEN=<secret-at-least-24-characters>
```

Prefer private monitoring networks/VPNs even when application-level authentication is enabled. Do not place the token in this repository or directly in a committed compose file.

## Reverse proxy and firewall

The validator application should not be bound directly to a public Internet interface without a reviewed proxy/network policy.

The examples in this directory demonstrate the intended layering:

```text
Internet
   ↓
reverse proxy / rate limits / TLS
   ↓
public read/transaction RPC

validator peers
   ↓
mTLS + certificate pinning + Ed25519 request authentication
   ↓
validator internal API
```

Review `nftables.example.conf` before use. The management address in that file is a documentation-only TEST-NET address and must be replaced.

## History and recovery

A full-history validator/archive node can export a genesis-anchored history artifact:

```bash
crakchain archive-export \
  --genesis /run/crakbit/genesis.json \
  --data /var/lib/crakbit \
  --output /var/backups/crakbit/history.json
```

A snapshot-bootstrapped node may verify and backfill that history later with `archive-verify` and `archive-import`. History import does not rewrite the snapshot-restored account state.

## Soak tests

Before any wider testnet announcement, run the multi-node monitor for sustained periods:

```bash
python scripts/soak_test.py \
  --node https://node1.example \
  --node https://node2.example \
  --node https://node3.example \
  --node https://node4.example \
  --duration-seconds 86400 \
  --interval-seconds 5 \
  --output runtime/soak-results.jsonl \
  --fail-on-divergence
```

Retain the output together with incident logs, validator logs, configuration versions and genesis hash.

## Still required before public-value use

- integration with an independently reviewed BFT consensus core,
- formal safety/liveness review,
- sustained multi-host partition/latency/load/Byzantine testing,
- production-grade key custody/HSM-equivalent controls,
- hardened monitoring/alert routing,
- production DDoS/reverse-proxy/network review,
- independent consensus/network/security audit.
