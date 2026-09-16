# Crakbit Chain Fault Harness

This directory provides a repeatable **development-only** transport fault harness using Toxiproxy. It is intended for latency, timeout and reachability experiments. It does not by itself prove Byzantine fault tolerance.

Start it after the four local validators are running:

```bash
cd blockchain/faults
docker compose -f docker-compose.toxiproxy.yml up -d
python control.py setup
```

Proxy ports:

- validator-1: `19101` -> local validator `9101`
- validator-2: `19102` -> local validator `9102`
- validator-3: `19103` -> local validator `9103`
- validator-4: `19104` -> local validator `9104`

Examples:

```bash
python control.py latency validator-2 --ms 1500 --jitter 250
python control.py timeout validator-3 --ms 5000
python control.py down validator-4
python control.py up validator-4
python control.py reset validator-2
```

To test validator-to-validator behavior through these proxies, generate a dedicated fault-test genesis whose peer URLs point at proxy endpoints reachable from each validator host/container. Do not mutate a running network's genesis file.

Recommended experiments:

1. one validator unreachable while quorum remains,
2. high latency on one validator,
3. two validators unreachable and expected loss of liveness,
4. delayed recovery and catch-up,
5. repeated validator restart during transaction load.

Byzantine message-generation tests remain separate work. A transport proxy can model delay/drop/timeout/corruption at the network layer but is not a substitute for consensus-level adversarial fixtures.
