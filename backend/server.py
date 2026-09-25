import os

import uvicorn

from backend.api import app


HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
PORT = int(os.getenv("BACKEND_PORT", "8000"))


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
