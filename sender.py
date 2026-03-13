import requests
import struct
import os
import json
import time
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RPC_URL = "http://acs:acs123@127.0.0.1:18443"

# 產生或載入金鑰
KEY_FILE = "C:\\ACS\\acs_private_key.pem"
PUBKEY_FILE = "C:\\ACS\\acs_public_key.pem"

def load_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    else:
        private_key = ec.generate_private_key(ec.SECP256K1())
        with open(KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()
            ))
        public_key = private_key.public_key()
        with open(PUBKEY_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        print(f"[ACS] new key generated, public key saved to {PUBKEY_FILE}")
    return private_key

def ecdh_encrypt(plaintext):
    # 生成臨時 ECDH 金鑰對
    ephemeral_key = X25519PrivateKey.generate()
    ephemeral_pub = ephemeral_key.public_key()
    
    # 載入接收方公鑰（這裡用自己的公鑰模擬）
    with open(PUBKEY_FILE, "rb") as f:
        peer_pub_bytes = f.read()
    
    # 用 HKDF 導出 AES 金鑰
    ephemeral_pub_bytes = ephemeral_pub.public_bytes_raw()
    shared_secret = os.urandom(32)  # 模擬 ECDH shared secret
    aes_key = HKDF(
        algorithm=crypto_hashes.SHA256(),
        length=32,
        salt=None,
        info=b"ACS_ECDH_V1"
    ).derive(shared_secret)
    
    # AES-GCM 加密
    aesgcm = AESGCM(aes_key)
    nonce_gcm = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce_gcm, plaintext, None)
    
    return ephemeral_pub_bytes[:8], ciphertext[:16]

def rpc(method, params=None):
    if params is None:
        params = []
    r = requests.post(RPC_URL, json={"jsonrpc":"1.0","method":method,"params":params})
    result = r.json()
    if result.get("error"):
        print(f"RPC ERROR [{method}]: {result['error']}")
        return None
    return result["result"]

def get_block_height():
    return rpc("getblockcount")

def sign_payload(private_key, data):
    signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    return signature

def write_audit_log(txid, height, action, signature_hex):
    log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "txid": txid,
        "block_height": height,
        "action": action,
        "signature": signature_hex
    }
    with open("C:\\ACS\\audit_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")
    print(f"[AUDIT] logged: {action} at height {height}")

private_key = load_or_create_key()
height = get_block_height()
nonce = os.urandom(8)
timestamp = int(time.time())

# 明文協議標頭，任何人都能識別
protocol_header = b'ACS_RESEARCH_V2'
action = b'UNLOCK_DOOR_01'
# Phase 5: ECDH 加密指令
ecdh_tag, encrypted_action = ecdh_encrypt(action)
print(f"[Phase5] ECDH encrypted action: {encrypted_action.hex()[:16]}...")

payload_to_sign = protocol_header + nonce + struct.pack(">I", timestamp) + action
signature = sign_payload(private_key, payload_to_sign)
sig_fingerprint = signature[:28]

payload = (
    protocol_header[:4] +
    nonce +
    struct.pack(">I", timestamp) +
    sig_fingerprint
)

print(f"protocol: ACS_RESEARCH_V2 (transparent)")
print(f"height: {height}")
print(f"nonce: {nonce.hex()}")
print(f"timestamp: {timestamp}")
print(f"payload size: {len(payload)} bytes")

# Phase 4: 地址跳變，每次用新地址
address = rpc("getnewaddress", ["", "bech32m"])
print(f"[Phase5] Taproot address: {address}")

print(f"[Phase4] new address: {address}")

utxos = rpc("listunspent")
if not utxos:
    print("no utxo, generating...")
    rpc("generatetoaddress", [101, address])
    utxos = rpc("listunspent")

utxo = utxos[0]
change = round(utxo["amount"] - 0.001, 8)
inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]}]
outputs = [{"data": payload.hex()}, {address: change}]

raw = rpc("createrawtransaction", [inputs, outputs])
signed = rpc("signrawtransactionwithwallet", [raw])
txid = rpc("sendrawtransaction", [signed["hex"]])
print(f"ACS tx sent: {txid}")

with open("C:\\ACS\\pending_txid.txt", "w") as f:
    f.write(txid)

write_audit_log(txid, height, "SEND_COMMAND", signature.hex())

# Phase 4: 噪音注入，發 1-3 筆假交易
import random
noise_count = random.randint(1, 3)
print(f"[Phase4] injecting {noise_count} noise tx...")
for i in range(noise_count):
    noise_address = rpc("getnewaddress", ["", "bech32"])
    noise_utxos = rpc("listunspent")
    if not noise_utxos:
        break
    noise_utxo = noise_utxos[0]
    noise_change = round(noise_utxo["amount"] - 0.001, 8)
    noise_inputs = [{"txid": noise_utxo["txid"], "vout": noise_utxo["vout"]}]
    noise_outputs = [{noise_address: noise_change}]
    noise_raw = rpc("createrawtransaction", [noise_inputs, noise_outputs])
    noise_signed = rpc("signrawtransactionwithwallet", [noise_raw])
    noise_txid = rpc("sendrawtransaction", [noise_signed["hex"]])
    print(f"[Phase4] noise tx {i+1}: {noise_txid[:16]}...")