# CoralOS & STUK: SipQuest Reveal Market

SipQuest adds a paid agent service named `sipquest-reveal`.

The CoralOS/STUK starter kit already provides the agent coordination loop and Solana devnet escrow settlement. SipQuest contributes the service payload, seller personas, and buyer ranking criteria that can be dropped into the starter kit fork points:

- `coral-agents/seller-agent/src/service.ts`
- `coral-agents/buyer-agent/src/sipquestBuyer.ts`
- `coral-agents/config/seller-personas.toml`

## Service Request

```json
{
  "vibe": "wildcard",
  "safeMode": true,
  "avoid": ["caffeine"],
  "setId": "launch-set",
  "customerPartyId": "optional",
  "wallet": "optional"
}
```

## Settlement

Run this through the CoralOS/STUK starter kit rails so the market still follows:

```text
WANT -> BID -> AWARD -> DEPOSITED -> DELIVERED -> RELEASED
```

The buyer should set:

```bash
BUYER_SERVICE=sipquest-reveal
BUYER_ARG='{"vibe":"wildcard","safeMode":true,"avoid":["caffeine"],"setId":"launch-set"}'
```

The seller output includes the reveal, safety proof, responsible-randomness fields, and a physical fulfillment reference for the Fetch/ASI:One box agent.
