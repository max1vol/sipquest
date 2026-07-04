# GCC: Public Funding Allocation Agent

SipQuest includes a reusable funding allocation agent for the GCC public funding / AI-for-good track.

The agent does not stop at a chat response. It takes structured applications, scores them with a transparent rubric, and emits a funding plan with:

- impact estimates
- counterfactual need
- milestone clarity
- verification strength
- open-source reuse
- delivery risk
- recommended allocation

Run:

```bash
python agents/gcc_public_funding_agent.py \
  --applications data/gcc/applications.json \
  --budget-gbp 7500
```

The rubric is intended to be portable: other grant programs can reuse the JSON input format, scoring components, and allocation output without adopting SipQuest hardware.
