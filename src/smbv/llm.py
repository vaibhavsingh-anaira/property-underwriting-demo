"""Gemini client, configured the same way as tampering-check / preinspection-car-ml."""
from __future__ import annotations
import json
import os
import threading
from smbv.config import load

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _credentials(c: dict):
    from google.oauth2 import service_account
    src = c.get("source", "adc")
    if src == "aws_secret":
        import boto3
        s = boto3.client("secretsmanager", region_name=c["secret_region"]).get_secret_value(SecretId=c["secret_name"])
        return service_account.Credentials.from_service_account_info(json.loads(s["SecretString"]), scopes=SCOPES)
    if src == "file":
        return service_account.Credentials.from_service_account_file(c["path"], scopes=SCOPES)
    return None  # adc


_LOCK = threading.Lock()
_CLIENT = None


def client():
    """One shared client per process. Built under a lock: a second client created by a racing thread would be
    garbage-collected mid-request, which closes its HTTP connection ('client has been closed')."""
    global _CLIENT
    with _LOCK:
        if _CLIENT is None:
            from google import genai
            g = load()["gemini"]
            c = g.get("credentials") or {}
            if c.get("source") == "api_key":
                _CLIENT = genai.Client(api_key=os.environ[c.get("api_key_env", "GEMINI_API_KEY")])
            else:
                _CLIENT = genai.Client(vertexai=True, project=g["project"], location=g.get("location", "us-central1"),
                                       credentials=_credentials(c))
        return _CLIENT


def model() -> str:
    return load()["gemini"]["model"]
