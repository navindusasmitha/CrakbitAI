# Validator Security / Rotation Runbook

**Scope:** Crakbit Chain research devnet and public-testnet preparation only.

## Separate key material

Each validator should keep these identities separate:

1. **Consensus identity** — Ed25519 validator key used to sign Crakbit consensus/request messages.
2. **Transport identity** — X.509 private key/certificate used for TLS/mTLS.

Do not reuse wallet keys, seed phrases or exchange/custodial keys for either role.

## Storage requirements

- Never commit private keys or certificates containing private key material to Git.
- Restrict validator key files to the service account running the node.
- Keep an encrypted offline backup of validator identity material.
- Prefer a secrets manager/HSM for any future production-grade deployment.
- Keep CA signing keys offline wherever practical.

## TLS certificate issuance

For v0.11 mTLS mode, each validator certificate should:

- chain to the configured validator CA,
- contain the exact hostname used in the validator's HTTPS `peer_url` as a SAN,
- be usable for both server and client authentication when the included launcher is used,
- have a short, documented validity period,
- be tracked by SHA-256 leaf certificate fingerprint when peer pinning is enabled.

Generate a fingerprint for the pin map:

```bash
python scripts/cert_fingerprint.py /run/secrets/validator.crt
```

The pin file format is:

```json
{
  "crk1VALIDATOR_ADDRESS": "64-lowercase-hex-sha256-fingerprint"
}
```

## Planned certificate rotation procedure

1. Issue a new certificate/key pair from the approved validator CA.
2. Verify hostname/SAN and validity dates.
3. Calculate and distribute the new fingerprint out-of-band.
4. During a controlled maintenance window, update peer pin maps to the new expected certificate.
5. Restart one validator at a time with the new certificate.
6. Confirm `/transport/status`, `/peers`, `/health`, consensus height and authenticated peer telemetry.
7. Remove the old pin after every peer has moved to the new certificate.
8. Revoke/destroy the old private key according to operator policy.
9. Record the rotation in the incident/change log.

The current single-fingerprint pin map does not implement an automatic dual-pin grace period. Operators must coordinate rotation carefully; automatic overlap/rotation is future work.

## Consensus key compromise

The current research chain does not support safe dynamic validator-set/key rotation. If a validator Ed25519 key is suspected compromised:

1. isolate the validator host,
2. preserve logs/evidence,
3. stop using the compromised key,
4. treat the existing devnet as potentially compromised,
5. coordinate a new genesis / validator set for a fresh development network,
6. publish an incident note for any public testnet participants.

Do not silently replace a consensus key in an existing genesis file.

## Transport key compromise

If only the X.509 transport key is compromised:

1. revoke/retire the certificate,
2. issue a replacement certificate/key,
3. update peer pin maps,
4. restart the affected validator in a controlled window,
5. verify Ed25519 validator identity independently through the signed challenge/response endpoint.

## Incident evidence

Retain, where available:

- consensus event journal,
- equivocation evidence,
- Prometheus/Grafana timeline,
- validator logs,
- certificate fingerprints and validity periods,
- backup manifests,
- integrity/doctor reports,
- exact software commit SHA and genesis fingerprint.

This runbook is operational guidance for the research project and is not a substitute for an independent security review.
