\# ACS 2.0 — Authenticated Command System



> 無法被追蹤、無法被偽造、無法被否認的區塊鏈 IoT 指令傳遞系統



\## 簡介



ACS 2.0 使用比特幣 Regtest 區塊鏈作為 IoT 指令傳遞總線，透過 OP\_RETURN 欄位傳遞加密指令，Monitor 端根據確認數階梯式觸發實體硬體動作。



\## 系統架構

```

Sender → Bitcoin Regtest → Monitor → 硬體觸發

```



\## 核心特性



\- 🔐 ECDSA 公鑰簽章，無私鑰者無法偽造指令

\- ⏱️ Timestamp 防重放，±600秒有效期

\- 📋 公開審計日誌，每個動作都可追溯

\- 🔀 地址跳變 + 噪音注入，隱蔽真實指令

\- 🔒 ECDH + AES-256-GCM 加密指令內容

\- 🌿 Taproot 地址，交易外觀與普通交易相同



\## 確認階梯狀態機



| 確認數 | 狀態 | 動作 |

|--------|------|------|

| 0 | ALERT | 偵測到指令，開始監控 |

| 3 | READY | 預備執行 |

| 6 | EXECUTE | 觸發實體硬體 |



\## 環境需求



\- Bitcoin Core v28+ (Regtest)

\- Python 3.12+

\- 套件：`pip install pyzmq requests cryptography`



\## 使用方式



啟動 Monitor：

```bash

python monitor.py

```



發送指令：

```bash

python sender.py

```



\## 開發進度



\- \[x] Phase 1：ZMQ 即時監聽

\- \[x] Phase 2：Timestamp 防重放驗證

\- \[x] Phase 3：0/3/6 確認階梯狀態機

\- \[x] Phase 4：地址跳變 + 噪音注入

\- \[x] Phase 5：ECDH 加密 + Taproot

\- \[ ] Phase 6：真實硬體 GPIO 接線



\## 作者



Andy Lin — 電子工程學系專題 2026

