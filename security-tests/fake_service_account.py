"""Prints a THROWAWAY Firebase service-account JSON (random RSA key, fake project). For local/CI start checks only:
it lets a production-mode server start and exercise real token verification without any real credential."""

import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
print(
    json.dumps(
        {
            "type": "service_account",
            "project_id": "demo-cratescan",
            "private_key_id": "fake",
            "private_key": pem,
            "client_email": "fake@demo-cratescan.iam.gserviceaccount.com",
            "client_id": "1",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
)
