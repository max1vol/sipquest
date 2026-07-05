from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):
        env_path = Path(_args[0]) if _args else Path(".env")
        if not env_path.exists():
            return False
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return True


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    try:
        from uagents_core.utils.registration import (
            RegistrationRequestCredentials,
            register_chat_agent,
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing uAgents dependency. Install project requirements first, for example: "
            "python3 -m pip install -r requirements.txt"
        ) from exc

    agent_name = os.getenv("AGENT_NAME", "sipquest-box-agent")
    agent_endpoint = os.getenv(
        "AGENT_ENDPOINT",
        "https://sipquest-agent-endpoint.max1-volovich.workers.dev/submit",
    )

    missing = [
        name
        for name in ("AGENTVERSE_KEY", "AGENT_SEED_PHRASE")
        if not os.getenv(name)
    ]
    if missing:
        raise SystemExit(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Add them to .env or export them before running this script."
        )

    register_chat_agent(
        agent_name,
        agent_endpoint,
        active=True,
        credentials=RegistrationRequestCredentials(
            agentverse_api_key=os.environ["AGENTVERSE_KEY"],
            agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],
        ),
    )
    print(f"Registered {agent_name} at {agent_endpoint}")


if __name__ == "__main__":
    main()
