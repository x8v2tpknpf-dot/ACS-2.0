# ACS 2.0 — Authenticated Command System

> An IoT command delivery system built on Bitcoin that cannot be tracked, forged, or repudiated.

---

## Overview

ACS 2.0 uses a **Bitcoin Regtest blockchain** as a tamper-proof IoT command bus.
Commands are encrypted and embedded in transaction `OP_RETURN` fields. A monitoring daemon watches the chain and triggers physical hardware actions once the required number of block confirmations is reached.

```
Sender ──► Bitcoin Regtest Node ──► Monitor ──► Hardware Trigger (GPIO)
           (OP_RETURN payload)       (ZMQ)        Phase 6
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🔐 **ECDSA Signatures** | Commands signed with a private key — impossible to forge without it |
| ⏱️ **Replay Attack Prevention** | Timestamp validated within ±600 seconds (Phase 2) |
| 📋 **Immutable Audit Log** | Every action appended to `audit_log.json` with txid and block height |
| 🔀 **Address Rotation + Noise** | New Bech32 address per tx; 1–3 decoy transactions injected (Phase 4) |
| 🔒 **ECDH + AES-256-GCM** | Command payload encrypted with X25519 key exchange (Phase 5) |
| 🌿 **Taproot Addresses** | Transactions use `bech32m` format, indistinguishable from normal transfers |
| ⚡ **GPIO Hardware Trigger** | Simulated RPi.GPIO interface with full audit logging (Phase 6) |

---

## Confirmation Ladder State Machine

The monitor reacts at three confirmation thresholds:

| Confirmations | State | Action |
|:---:|---|---|
| 0 | `ALERT` | Signal detected — begin tracking txid |
| 3 | `READY` | Preparing to execute |
| 6 | `EXECUTE` | Trigger hardware action (`UNLOCK_DOOR_01`) |

---

## File Structure

```
ACS/
├── sender.py            # Phase 1–5: build, sign, encrypt & broadcast command tx
├── monitor.py           # Phase 1–3: ZMQ listener, timestamp check, state machine
├── gpio_mock.py         # Phase 6: simulated RPi.GPIO (setup/output/cleanup)
├── phase6_listener.py   # Phase 6: ZMQ → OP_RETURN → decrypt → GPIO trigger
├── demo_run.py          # Phase 6: end-to-end simulation demo
├── audit_log.json       # Append-only audit trail (auto-generated)
├── gpio_log.txt         # GPIO trigger history (auto-generated)
└── pending_txid.txt     # IPC file: sender → monitor handoff
```

---

## Requirements

- **Bitcoin Core v28+** running in Regtest mode with ZMQ enabled
- **Python 3.10+**
- Dependencies:

```bash
pip install pyzmq requests cryptography
```

---

## Quick Start

### 1. Start Bitcoin Core (Regtest)

```bash
bitcoind -regtest \
  -rpcuser=acs \
  -rpcpassword=acs123 \
  -zmqpubrawtx=tcp://127.0.0.1:28333 \
  -daemon
```

### 2. Run the Phase 6 Simulation Demo

```bash
cd C:\ACS
python demo_run.py
```

This single command will:
1. Self-test `gpio_mock` (PIN 17 HIGH → LOW cycle)
2. Start the Phase 6 ZMQ listener in a background thread
3. Execute `sender.py` to broadcast an encrypted `UNLOCK_DOOR_01` command
4. Wait for the transaction to arrive over ZMQ
5. Validate the ACS protocol header + timestamp
6. Fire `gpio_mock.trigger_lock(pin=17, duration=3s)`
7. Print the final GPIO log and a completion summary

### 3. Run Components Individually

**Start the monitor (Phase 1–3 only):**
```bash
python monitor.py
```

**Send a command transaction (Phase 1–5):**
```bash
python sender.py
```

**Start the Phase 6 GPIO listener standalone:**
```bash
python phase6_listener.py
```

---

## Phase 6 — GPIO Hardware Simulation

Phase 6 completes the end-to-end pipeline by replacing the placeholder `UNLOCK_DOOR_01` print statement with a real GPIO trigger layer.

### `gpio_mock.py`

Provides a drop-in mock for `RPi.GPIO` so the system can be developed and tested on any platform without physical hardware:

```python
import gpio_mock

gpio_mock.trigger_lock(pin=17, duration_sec=3)
```

Console output:
```
[2026-03-28 19:07:14] GPIO PIN 17 → HIGH (鎖已開啟 🔓)
[2026-03-28 19:07:17] GPIO PIN 17 → LOW  (鎖已關閉 🔒)
```

All events are appended to `gpio_log.txt` with timestamps.

### Porting to Real Hardware (Raspberry Pi)

To run on a physical RPi, replace the `gpio_mock` import with the real library:

```python
# phase6_listener.py  — swap this line:
import gpio_mock as GPIO

# with:
import RPi.GPIO as GPIO
```

No other code changes are required — the interface is identical.

---

## Protocol Payload Structure

The `OP_RETURN` field carries a 44-byte ACS payload:

```
Bytes  0– 3   Protocol header        b'ACS_'
Bytes  4–11   Nonce (anti-replay)    8 bytes random
Bytes 12–15   Timestamp              uint32 big-endian (Unix epoch)
Bytes 16–43   Signature fingerprint  28-byte ECDSA sig prefix
```

---

## Development Progress

- [x] **Phase 1** — ZMQ real-time transaction monitoring
- [x] **Phase 2** — Timestamp replay-attack prevention
- [x] **Phase 3** — 0 / 3 / 6 confirmation ladder state machine
- [x] **Phase 4** — Address rotation + noise transaction injection
- [x] **Phase 5** — ECDH encryption (X25519 + AES-256-GCM) + Taproot addresses
- [x] **Phase 6** — GPIO hardware trigger simulation (`gpio_mock`, `phase6_listener`, `demo_run`)

---

## Author

**Andy Lin** — Electronic Engineering Department Capstone Project, 2026
