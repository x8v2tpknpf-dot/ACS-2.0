# ══════════════════════════════════════════════════════════════════════════════
# gpio_mock.py  ─  模擬 RPi.GPIO 介面
# ACS 2.0 Phase 6 - Hardware GPIO Simulation
# ══════════════════════════════════════════════════════════════════════════════

import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

GPIO_LOG = Path("C:/ACS/gpio_log.txt")

# ── 常數（對應 RPi.GPIO 介面）────────────────────────────────────────────────
BCM  = "BCM"
BOARD = "BOARD"
OUT  = "OUT"
IN   = "IN"
HIGH = True
LOW  = False


# ── 內部工具 ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(msg: str) -> None:
    """同步寫入 stdout 與 gpio_log.txt。"""
    line = f"[{_ts()}] {msg}"
    print(line)
    sys.stdout.flush()
    try:
        with open(GPIO_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── 模擬 RPi.GPIO 介面 ────────────────────────────────────────────────────────

def setmode(mode: str) -> None:
    """設定 GPIO 編號模式（BCM / BOARD）。"""
    _log(f"GPIO.setmode({mode})")


def setup(pin: int, mode: str) -> None:
    """設定指定 pin 為輸入/輸出模式。"""
    _log(f"GPIO.setup(pin={pin}, mode={mode})")


def output(pin: int, state: bool) -> None:
    """
    設定 pin 輸出狀態。
    HIGH → 鎖已開啟；LOW → 鎖已關閉
    """
    UNLOCK = "\U0001F513"  # 🔓
    LOCK   = "\U0001F512"  # 🔒
    ARROW  = "\u2192"      # →
    if state:
        _log(f"GPIO PIN {pin} {ARROW} HIGH (\u9396\u5df2\u958b\u555f {UNLOCK})")
    else:
        _log(f"GPIO PIN {pin} {ARROW} LOW  (\u9396\u5df2\u95dc\u9589 {LOCK})")


def cleanup() -> None:
    """釋放所有 GPIO 資源。"""
    _log("GPIO.cleanup() - 所有 GPIO 資源已釋放")


# ── 主觸發函式 ─────────────────────────────────────────────────────────────────

def trigger_lock(pin: int = 17, duration_sec: float = 3.0) -> None:
    """
    模擬電子鎖觸發流程：
      1. 設定 pin 模式
      2. OUTPUT HIGH  → 通電開門
      3. 等待 duration_sec 秒
      4. OUTPUT LOW   → 斷電關門
      5. cleanup

    Parameters
    ----------
    pin          : GPIO 腳位（預設 17，對應 BCM GPIO 17）
    duration_sec : 保持開啟秒數（預設 3 秒）
    """
    _log(f"--- trigger_lock 開始 (pin={pin}, duration={duration_sec}s) ---")
    setmode(BCM)
    setup(pin, OUT)

    # 開鎖
    output(pin, HIGH)

    # 保持開啟
    _log(f"等待 {duration_sec} 秒後關閉...")
    time.sleep(duration_sec)

    # 關鎖
    output(pin, LOW)
    cleanup()
    _log(f"--- trigger_lock 結束 ---")


# ── 單獨執行測試 ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== gpio_mock 自我測試 ===")
    trigger_lock(pin=17, duration_sec=2)
    print(f"log 已寫入: {GPIO_LOG}")
