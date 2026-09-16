# Crakbit Chain v0.9 Development Observability

This directory contains a **development-only** Prometheus + Grafana stack for the four-validator local devnet.

It is not a production monitoring deployment and the included Grafana password must be changed before exposing the service to any network.

## Start the blockchain first

From `blockchain/`:

```bash
docker compose up --build
```

The validator RPC endpoints should be available on ports `9101` through `9104`.

## Start Prometheus + Grafana

In another terminal:

```bash
cd blockchain/ops
docker compose -f docker-compose.observability.yml up -d
```

Development endpoints:

- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`
- Grafana development login: `admin / crakbit-devnet-change-me`

Change the Grafana password before using this outside an isolated local machine.

## What is monitored

The pre-provisioned dashboard reads the existing `/metrics/prometheus` endpoint and charts:

- chain height by validator,
- consensus round,
- mempool transaction count,
- authenticated validator views,
- equivocation evidence count,
- consensus lock state.

The stack reaches host-published validator ports through `host.docker.internal`. The compose file adds a host-gateway mapping for Linux Docker hosts.

## v0.9 operator integrity commands

Run a quick database/accounting check:

```bash
crakchain doctor --genesis runtime/genesis.json --data runtime/node1-data
```

Run the full local-history/certificate/index check:

```bash
crakchain doctor --genesis runtime/genesis.json --data runtime/node1-data --full
```

Create an online verified SQLite backup:

```bash
crakchain backup-create \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/backups/node1.sqlite3
```

Verify the backup later:

```bash
crakchain backup-verify \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --full
```

The backup manifest records the chain identity, height, tip hash, file size and SHA-256 digest. The verifier also runs the v0.9 integrity checks against the copied database.

## Production gaps

Before a public-value network, monitoring still needs authenticated dashboards, alert routing, durable metric storage, log aggregation, SLOs, incident-response procedures and independent review. The blockchain itself also still needs mature BFT lock/unlock semantics and reviewed mutually authenticated encrypted validator transport.
