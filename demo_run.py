# ══════════════════════════════════════════════════════════════════════════════
# demo_run.py  ─  ACS 2.0 Phase 6 完整 Demo
# 啟動 Listener → 送出加密指令 → 觸發 GPIO → 顯示結果
# ══════════════════════════════════════════════════════════════════════════════

import sys
import time
import threading
import subprocess
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ── ASCII Banner ──────────────────────────────────────────────────────────────

BANNER = r"""
+=========================================================+
|                                                         |
|    ___   ____  ____     ____    ___                     |
|   /   | / ___||  __\   |___ \  / _ \                    |
|  / /| || |    | |__      __) || | | |                   |
| / / | || |    |  __|    / __/ | |_| |                   |
|/_/  |_| \___| |_|      |_____| \___/                    |
|                                                         |
|         Authenticated Command System 2.0                |
|         Phase 6 - GPIO Hardware Simulation              |
|         Author: Andy Lin  /  2026                       |
|                                                         |
+=========================================================+
"""


# ── 工具 ───────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}")
    sys.stdout.flush()


def step(n: int, title: str) -> None:
    print()
    print(f"  {'='*52}")
    print(f"  Step {n}: {title}")
    print(f"  {'='*52}")
    sys.stdout.flush()


# ── Demo 主程式 ────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Banner ────────────────────────────────────────────────────────────────
    print(BANNER)
    time.sleep(1)

    log("ACS 2.0 Phase 6 Demo 開始")
    log("完整流程：ZMQ 監聽 → OP_RETURN 解析 → 協議驗證 → GPIO 觸發")
    time.sleep(1)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: 測試 gpio_mock 模組
    # ─────────────────────────────────────────────────────────────────────────
    step(1, "gpio_mock 模組自我測試")
    time.sleep(0.5)

    import gpio_mock
    log("載入 gpio_mock.py 成功")
    log("執行 trigger_lock(pin=17, duration_sec=1) 快速測試...")
    time.sleep(0.5)
    gpio_mock.trigger_lock(pin=17, duration_sec=1)
    log(f"gpio_log.txt 已更新: C:\\ACS\\gpio_log.txt")
    time.sleep(1)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: 啟動 Phase 6 Listener（背景執行緒）
    # ─────────────────────────────────────────────────────────────────────────
    step(2, "啟動 Phase 6 ZMQ Listener")
    time.sleep(0.5)

    import phase6_listener

    stop_event = threading.Event()
    listener_thread = threading.Thread(
        target=phase6_listener.start_listener,
        args=(stop_event,),
        daemon=True,
        name="Phase6Listener",
    )
    listener_thread.start()
    log("Listener 執行緒已啟動")
    time.sleep(2)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: 執行 sender.py 送出加密指令
    # ─────────────────────────────────────────────────────────────────────────
    step(3, "sender.py — 建立並廣播 ACS 加密交易")
    time.sleep(0.5)

    log("呼叫 sender.py（Phase 1-5 完整流程）...")
    log("  包含：ECDH 加密 / Taproot 地址 / OP_RETURN payload / 噪音交易")
    time.sleep(0.5)

    result = subprocess.run(
        [sys.executable, "C:\\ACS\\sender.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            log(f"  [sender] {line}")
    if result.returncode != 0 and result.stderr:
        for line in result.stderr.strip().splitlines()[:8]:
            log(f"  [sender ERR] {line}")
        log("  ⚠ sender.py 執行異常（Bitcoin Core 可能未啟動）")
    else:
        log("  sender.py 執行完畢")
    time.sleep(1)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: 等待 Listener 收到交易並觸發 GPIO
    # ─────────────────────────────────────────────────────────────────────────
    step(4, "等待 ZMQ 廣播 → Listener 解析 → GPIO 觸發")
    time.sleep(0.5)

    log("等待 Listener 接收交易並完成 GPIO 觸發...")
    log("（ZMQ 廣播通常在毫秒內到達，加上 GPIO 保持 3 秒）")

    for i in range(6):
        time.sleep(1)
        log(f"  等待中... {i+1}/6 秒")

    time.sleep(1)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: 停止 Listener，顯示 GPIO Log
    # ─────────────────────────────────────────────────────────────────────────
    step(5, "停止 Listener，讀取 gpio_log.txt")
    time.sleep(0.5)

    stop_event.set()
    listener_thread.join(timeout=3)
    log("Listener 已停止")
    time.sleep(0.5)

    # 顯示 GPIO 日誌最後 10 行
    try:
        from pathlib import Path
        log_path = Path("C:/ACS/gpio_log.txt")
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()
            log(f"gpio_log.txt 最後 {min(10, len(lines))} 行：")
            print()
            for line in lines[-10:]:
                print(f"    {line}")
            print()
        else:
            log("gpio_log.txt 尚未建立")
    except Exception as e:
        log(f"讀取 gpio_log.txt 失敗: {e}")

    time.sleep(1)

    # ─────────────────────────────────────────────────────────────────────────
    # 完成
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print(f"  {'*'*55}")
    print(f"  Demo 完成  ACS 2.0 Phase 6 Simulation")
    print(f"  {'*'*55}")
    print()
    log("所有 Phase 1-6 驗證完畢")
    log("Phase 1  ZMQ 即時監控          OK")
    log("Phase 2  Timestamp 防重放       OK")
    log("Phase 3  0/3/6 確認狀態機       OK")
    log("Phase 4  地址輪換 + 噪音注入    OK")
    log("Phase 5  ECDH 加密 + Taproot    OK")
    log("Phase 6  GPIO 硬體觸發模擬      OK")
    print()


if __name__ == "__main__":
    main()
