import zmq
import struct
import requests
import json
import time
import threading
import hashlib

RPC_URL = "http://acs:acs123@127.0.0.1:18443"
ZMQ_TX = "tcp://127.0.0.1:28333"
PROTOCOL_HEADER = b'ACS_'

pending = {}
pending_lock = threading.Lock()

def rpc(method, params=None):
    if params is None:
        params = []
    try:
        r = requests.post(RPC_URL, json={"jsonrpc":"1.0","method":method,"params":params}, timeout=5)
        result = r.json()
        if result.get("error"):
            return None
        return result["result"]
    except:
        return None

def get_confirmations(txid):
    result = rpc("gettransaction", [txid])
    if result and "confirmations" in result:
        return result["confirmations"]
    result = rpc("getrawtransaction", [txid, True])
    if result and "confirmations" in result:
        return result["confirmations"]
    return 0

def write_audit_log(txid, action, status):
    log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "txid": txid,
        "action": action,
        "status": status
    }
    with open("C:\\ACS\\audit_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")

def trigger_action(txid, confirmations):
    if confirmations == 0:
        print(f"[0-conf] ALERT - signal detected")
        print(f"         txid: {txid[:16]}...")
        write_audit_log(txid, "ALERT", "0-conf")
    elif confirmations >= 6:
        print(f"[6-conf] EXECUTE - final action!")
        print(f"         >> UNLOCK_DOOR_01 executed <<")
        print(f"         txid: {txid[:16]}...")
        write_audit_log(txid, "EXECUTE", "6-conf")
    elif confirmations >= 3:
        print(f"[3-conf] READY - preparing action")
        print(f"         txid: {txid[:16]}...")
        write_audit_log(txid, "READY", "3-conf")

def parse_op_return(raw_tx):
    try:
        pos = raw_tx.find(b'\x6a')
        if pos == -1:
            return None
        length = raw_tx[pos + 1]
        data = raw_tx[pos + 2: pos + 2 + length]
        return data
    except:
        return None

def verify_timestamp(payload):
    try:
        ts = struct.unpack(">I", payload[12:16])[0]
        now = int(time.time())
        return abs(now - ts) <= 600
    except:
        return False

def confirmation_tracker():
    print("[tracker] started")
    notified = {}
    while True:
        time.sleep(3)
        # 從檔案讀取最新 txid
        try:
            with open("C:\\ACS\\pending_txid.txt", "r") as f:
                file_txid = f.read().strip()
            if file_txid:
                with pending_lock:
                    if file_txid not in pending:
                        pending[file_txid] = time.time()
                        print(f"[tracker] tracking txid: {file_txid[:16]}...")
        except:
            pass

        with pending_lock:
            txids = list(pending.keys())

        for txid in txids:
            confs = get_confirmations(txid)
            print(f"[tracker] {txid[:16]}... confs={confs}")
            last = notified.get(txid, -1)
            if confs >= 6 and last < 6:
                trigger_action(txid, 6)
                notified[txid] = 6
                with pending_lock:
                    pending.pop(txid, None)
            elif confs >= 3 and last < 3:
                trigger_action(txid, 3)
                notified[txid] = 3

tracker = threading.Thread(target=confirmation_tracker, daemon=True)
tracker.start()

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(ZMQ_TX)
socket.setsockopt(zmq.SUBSCRIBE, b"rawtx")
socket.setsockopt(zmq.RCVTIMEO, 1000)

print("[ACS Monitor] Phase 3 start...")

while True:
    try:
        msg = socket.recv_multipart()
        raw_tx = msg[1]
        data = parse_op_return(raw_tx)

        if not data or data[:4] != PROTOCOL_HEADER:
            continue

        if not verify_timestamp(data):
            print("[ACS] FAIL - timestamp invalid")
            continue

        # 從 sender 的檔案取得正確 txid
        try:
            with open("C:\\ACS\\pending_txid.txt", "r") as f:
                txid = f.read().strip()
        except:
            continue

        with pending_lock:
            pending[txid] = time.time()
        trigger_action(txid, 0)

    except zmq.Again:
        pass