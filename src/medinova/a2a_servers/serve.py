import argparse
import os

import uvicorn
from dotenv import load_dotenv

from medinova.agents.config_loader import load_a2a_config
from medinova.a2a_servers.app import create_a2a_app

def run_server(agent_name: str) -> None:
    load_dotenv()

    port = load_a2a_config(agent_name)["port"]
    host = os.getenv("A2A_BIND_HOST", "127.0.0.1")
    public_url = os.getenv(
        f"{agent_name.upper()}_AGENT_PUBLIC_URL",
        f"http://127.0.0.1:{port}",
    )

    app = create_a2a_app(agent_name, public_url)
    print(f"{agent_name}: {public_url}")
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an A2A agent server")
    parser.add_argument("agent_name", help="Name defined under a2a_servers")
    args = parser.parse_args()
    run_server(args.agent_name)


if __name__ == "__main__":
    main()
