# Crakbit Validator Remote-Signer / Protected-Key Guidance

**Status:** architecture and operator guidance for public-testnet/mainnet-candidate work. This document does not claim that a production HSM or remote signer is currently deployed.

Crakbit's external consensus path uses CometBFT. A production validator should minimize the number of processes and hosts that can directly access its consensus signing key.

## Key separation

Do not reuse key material across roles.

| Role | Expected key | Exposure model |
| --- | --- | --- |
| CometBFT consensus validator | CometBFT private-validator signing key | Highest protection; remote signer/HSM-equivalent preferred |
| CometBFT P2P node | Node identity key | Validator host/network identity only |
| Crakbit research validator | Research/devnet Ed25519 key | Never promoted to production |
| Crakbit user wallet | User Ed25519 key | Client/user custody |
| Validator TLS | TLS private key | Certificate lifecycle/rotation |
| Release signer | Dedicated release Ed25519 key | Offline/protected release workflow |
| Faucet | Dedicated funded testnet wallet | Public-testnet service only |
| Mining Lab reward | Dedicated funded testnet wallet | Public-testnet service only |

Compromise of one role must not automatically compromise another.

## Target production shape

```text
CometBFT validator process
        │
        │ authenticated local/private signer protocol
        ▼
Remote signer / HSM-backed signer
        │
        └── protected consensus private key
```

The validator host should possess only the material necessary to contact the signer. The signing key should not need to exist as an ordinary plaintext file in the validator process filesystem.

## Required properties

A production signer design should provide:

- explicit chain/network binding where supported,
- prevention of double-signing across height/round/step,
- authenticated and encrypted signer transport when not strictly local,
- strict allow-list of validator clients,
- audit/event logging without private-key leakage,
- rate/availability monitoring,
- backup and disaster-recovery process,
- key rotation/replacement process,
- fail-closed behavior on corrupted signer state,
- documented behavior during network partitions,
- protection against restoring two active signer copies from the same backup.

## Double-signing protection

A validator key compromise is serious, but accidental duplicate signer activation is also dangerous. Operators must not clone one private-validator key onto two live validator processes.

Before any production launch, test at minimum:

1. validator process restart,
2. signer process restart,
3. signer temporarily unavailable,
4. validator host replacement,
5. restore from signer backup,
6. attempted stale signer-state restore,
7. concurrent duplicate-validator startup,
8. key rotation with no double-sign interval.

The expected result for unsafe/stale signing state is to stop signing rather than guess.

## Remote signer network boundary

If the signer is not on the same machine:

- put it on a private/explicitly authorized network,
- authenticate both ends,
- encrypt transport,
- apply network allow-lists/firewall rules,
- do not expose signer endpoints to public RPC users,
- monitor unexpected connection attempts,
- avoid depending only on source IP for identity.

## Backup rules

- Encrypt backups at rest.
- Restrict backup access separately from validator-host access.
- Record signer-state version/height information required for safe restore.
- Test restore procedures before relying on them.
- Never upload validator private keys or signer backups to public Git repositories, chats or issue trackers.
- Never move private keys between operators to simplify a genesis ceremony.

## Rotation / compromise response

A reviewed validator lifecycle must define how to:

- stop a compromised validator,
- revoke/replace credentials,
- update validator set membership where protocol/governance permits,
- rotate TLS credentials separately from consensus keys,
- preserve evidence/logs for incident review,
- communicate operator actions without publishing secrets.

The current Crakbit research configuration does not yet define final production validator governance or emergency removal semantics.

## Testnet rollout stages

### Stage A — local lab

Plain local CometBFT validator keys are acceptable for disposable isolated testing. Never reuse them later.

### Stage B — independent-host public testnet

Use separate hosts/operators and begin exercising remote-signer-like separation or protected signing. Run key-loss/restart/partition drills and record evidence.

### Stage C — production candidate

Require an independently reviewed signer/HSM-equivalent design, documented operational ownership, tested disaster recovery and monitored failover procedures.

## What v0.16 does and does not do

v0.16 provides this custody model, key-separation rules, multi-host health tooling and lab generation. It does **not** deploy an HSM, choose a commercial signer product, migrate existing validator keys automatically or satisfy the mainnet validator-key gate by documentation alone.

Any production implementation should be reviewed against the exact CometBFT version, signer protocol and operator environment actually deployed.
