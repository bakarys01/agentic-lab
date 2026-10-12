import os

import uvicorn

from medinova.backend.api import app


HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
PORT = int(os.getenv("BACKEND_PORT", "8000"))
TRUSTED_PROXY_IPS = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        proxy_headers=True,
        forwarded_allow_ips=TRUSTED_PROXY_IPS,
    )