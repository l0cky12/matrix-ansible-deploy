#!/usr/bin/env python3
"""Generate a Matrix Synapse signing key in YAML format.
Prints to stdout. Usage: python3 generate_signing_key.py
"""
try:
    from signedjson import key as sk
except ImportError:
    from synapse.crypto import signing_key as sk
import sys

key = sk.generate_signing_key("synapse")
key_id = key.alg + ":" + key.version
print(f"{key_id}: private: {sk.encode_signing_key_base64(key).decode()}")