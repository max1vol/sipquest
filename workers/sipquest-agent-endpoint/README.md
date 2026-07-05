# SipQuest Agent Endpoint Worker

This Worker exposes a public `/submit` URL for Agentverse and forwards requests to a real SipQuest uAgent origin.

It does not run the Python uAgent itself. Run `agents/sipquest_box_agent.py` somewhere reachable over HTTPS, then set `AGENT_ORIGIN_URL` to that public origin without `/submit`.

## Deploy

```bash
npm install
npx cf auth login
AGENT_ORIGIN_URL=https://<agent-origin-host> npx cf deploy
```

If `npx cf deploy` succeeds, use this as the Agentverse endpoint:

```text
https://<worker-name>.<workers-subdomain>.workers.dev/submit
```

## Configure Agent Origin

For a local uAgent exposed through a tunnel:

```bash
export AGENT_ENDPOINT="https://<tunnel-host>/submit"
export AGENT_MAILBOX=false
python3 agents/sipquest_box_agent.py
```

Then deploy the Worker with that same tunnel origin, without `/submit`:

```bash
AGENT_ORIGIN_URL=https://<tunnel-host> npx cf deploy
```

The Worker health check is:

```text
https://<worker-name>.<workers-subdomain>.workers.dev/health
```
