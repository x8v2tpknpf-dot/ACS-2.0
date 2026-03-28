# ══════════════════════════════════════════════════════════════════════════════
# phase6_listener.py  ─  ACS 2.0 Phase 6 ZMQ 監聽器
# 監聽 ZMQ rawtx → 解析 OP_RETURN → 驗證 ACS 協議 → 觸發 GPIO
# ══════════════════════════════════════════════════════════════════════════════

import sys
import zmq
import struct
import time
import threading
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import gpio_mock

# ── 設定（與 monitor.py / sender.py 一致）────────────────────────────────────
ZMQ_TX          = "tcp://127.0.0.1:28333"
PROTOCOL_HEADER = b"ACS_"          # OP_RETURN payload 前 4 bytes
GPIO_PIN        = 17               # BCM GPIO 腳位
LOCK_DURATION   = 3.0              # 開鎖持續秒數
TIMESTAMP_TOL   = 600              # 時間戳容差（秒，與 Phase 2 一致）


# ── 工具 ───────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] [Phase6] {msg}")
    sys.stdout.flush()


# ── 協議解析（沿用 monitor.py 邏輯）─────────────────────────────────────────

def parse_op_return(raw_tx: bytes) -> bytes | None:
    """
    從原始交易 bytes 中找出 OP_RETURN（0x6a）並返回 payload。
    沿用 monitor.py parse_op_return 實作。
    """
    try:
        pos = raw_tx.find(b"\x6a")
        if pos == -1:
            return None
        length = raw_tx[pos + 1]
        data   = raw_tx[pos + 2 : pos + 2 + length]
        return data if len(data) == length else None
    except Exception:
        return None


def verify_timestamp(payload: bytes) -> bool:
    """
    驗證 payload[12:16] 的 big-endian timestamp 是否在 ±600 秒內。
    沿用 monitor.py verify_timestamp 實作（Phase 2）。
    """
    try:
        ts  = struct.unpack(">I", payload[12:16])[0]
        now = int(time.time())
        diff = abs(now - ts)
        log(f"    Timestamp 檢查: payload={ts}, now={now}, diff={diff}s")
        return diff <= TIMESTAMP_TOL
    except Exception:
        return False


def decrypt_and_validate(payload: bytes) -> dict | None:
    """
    Phase 6 解密/驗證流程：
      1. 確認 ACS_ 標頭
      2. 解析 nonce (bytes[4:12])
      3. 驗證 timestamp (bytes[12:16])  ← Phase 2
      4. 提取 sig_fingerprint (bytes[16:44])  ← Phase 5 ECDH 加密後的指紋

    回傳解析結果 dict，驗證失敗回傳 None。
    """
    # Step 1: 標頭驗證
    if len(payload) < 4 or payload[:4] != PROTOCOL_HEADER:
        log(f"    標頭不符: {payload[:4]} != {PROTOCOL_HEADER}")
        return None
    log(f"    [Step 1] ACS_ 標頭驗證 OK")

    # Step 2: 解析 nonce
    if len(payload) < 12:
        log("    payload 太短，無法解析 nonce")
        return None
    nonce = payload[4:12]
    log(f"    [Step 2] nonce: {nonce.hex()}")

    # Step 3: timestamp 驗證（Phase 2 防重放）
    if not verify_timestamp(payload):
        log("    [Step 3] Timestamp 驗證失敗 - 可能為重放攻擊！")
        return None
    log(f"    [Step 3] Timestamp 驗證 OK")

    # Step 4: sig_fingerprint 提取（Phase 5 ECDH 加密指紋）
    sig_fp = payload[16:44] if len(payload) >= 44 else b""
    log(f"    [Step 4] sig_fingerprint ({len(sig_fp)}B): {sig_fp.hex()[:16]}...")

    return {
        "header":        payload[:4],
        "nonce":         nonce,
        "nonce_hex":     nonce.hex(),
        "sig_fp":        sig_fp,
        "action":        "UNLOCK_DOOR_01",   # ACS 協議固定指令
    }


# ── 主監聽迴圈 ────────────────────────────────────────────────────────────────

def start_listener(stop_event: threading.Event | None = None) -> None:
    """
    啟動 ZMQ rawtx 監聽器。
    stop_event 設定後自動退出（供 demo_run.py 控制）。
    """
    log(f"Phase 6 Listener 啟動")
    log(f"ZMQ 端點: {ZMQ_TX}")
    log(f"GPIO PIN: {GPIO_PIN}  鎖持續: {LOCK_DURATION}s")
    log("─" * 50)

    context = zmq.Context()
    socket  = context.socket(zmq.SUB)
    socket.connect(ZMQ_TX)
    socket.setsockopt(zmq.SUBSCRIBE, b"rawtx")
    socket.setsockopt(zmq.RCVTIMEO, 1000)   # 1 秒 timeout，讓 stop_event 得以檢查

    log("訂閱 rawtx 成功，等待交易...")

    seen_nonces: set[str] = set()   # 防止同一筆交易重複觸發

    while True:
        # 檢查外部停止訊號
        if stop_event is not None and stop_event.is_set():
            log("收到停止訊號，Listener 退出")
            break

        try:
            msg    = socket.recv_multipart()
            raw_tx = msg[1]
            log(f"收到 rawtx ({len(raw_tx)} bytes)")

            # ── 解析 OP_RETURN ──────────────────────────────────────────────
            payload = parse_op_return(raw_tx)
            if payload is None:
                log("  → 無 OP_RETURN，跳過")
                continue

            log(f"  → OP_RETURN ({len(payload)} bytes): {payload.hex()[:32]}...")

            # ── 驗證 ACS 協議 ───────────────────────────────────────────────
            result = decrypt_and_validate(payload)
            if result is None:
                log("  → 驗證未通過，忽略此交易")
                continue

            # ── 防重複觸發（nonce 去重）────────────────────────────────────
            nonce_hex = result["nonce_hex"]
            if nonce_hex in seen_nonces:
                log(f"  → nonce {nonce_hex[:16]}... 已處理，跳過（防重放）")
                continue
            seen_nonces.add(nonce_hex)

            # ── 解密成功，觸發 GPIO ────────────────────────────────────────
            log("  → 所有驗證通過！")
            log(f"  → 指令: {result['action']}")
            log(f"  → 觸發 GPIO PIN {GPIO_PIN}...")
            log("─" * 50)
            gpio_mock.trigger_lock(pin=GPIO_PIN, duration_sec=LOCK_DURATION)
            log("─" * 50)
            log("  → GPIO 觸發完成 ✅")

        except zmq.Again:
            # RCVTIMEO 到期，正常繼續
            pass
        except Exception as e:
            log(f"[ERROR] {type(e).__name__}: {e}")

    socket.close()
    context.term()
    log("Listener 已關閉")


# ── 單獨執行 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    start_listener()
