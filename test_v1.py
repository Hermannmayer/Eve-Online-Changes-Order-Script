"""快速测试 EVE SSO v1 Token 端点是否可用"""
import requests
import base64
import sys

# 直接从 config.yaml 读取 - 用二进制模式避免编码问题
import yaml
with open("config.yaml", "rb") as f:
    cfg = yaml.safe_load(f)

client_id = cfg["esi"]["client_id"]
client_secret = cfg["esi"]["client_secret"]

auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

# 测试 v1 token 端点
print(f"Testing v1 endpoint: https://login.eveonline.com/oauth/token")
print(f"Client ID: {client_id[:8]}...")

try:
    resp = requests.post(
        "https://login.eveonline.com/oauth/token",
        data="grant_type=authorization_code&code=TEST_CODE",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth}"
        },
        timeout=15,
    )
    print(f"HTTP {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"Body (first 300 chars): {resp.text[:300]}")
except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}: {e}")
