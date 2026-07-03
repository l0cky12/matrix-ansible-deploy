#!/usr/bin/env python3
"""Generate a Matrix Synapse signing key in YAML format.
Prints to stdout. Uses openssl CLI (no Python package deps needed).

Output format: ed25519:<version> <base64_private_key>
"""
import subprocess
import base64
import random
import string
import sys


def generate_signing_key():
    """Generate an ed25519 signing key using openssl CLI (always on Debian)."""
    try:
        result = subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ed25519", "-outform", "DER"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except FileNotFoundError:
        print("Error: openssl not found on system", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: openssl failed: {e.stderr.decode()}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: openssl timed out generating key", file=sys.stderr)
        sys.exit(1)

    # PKCS#8 DER encoding of ed25519 private key:
    #   The raw 32-byte seed is always the last 32 bytes.
    #   Structure: 30 2E 02 01 00 30 05 06 03 2B 65 70 04 22 04 20 [32 bytes]
    raw_key = result.stdout[-32:]
    version = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    key_b64 = base64.b64encode(raw_key).decode("ascii")
    return version, key_b64


if __name__ == "__main__":
    version, key_b64 = generate_signing_key()
    print(f"ed25519:{version} {key_b64}")