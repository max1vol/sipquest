import { bindings, defineWorker } from "wrangler/experimental-config";

export default defineWorker({
  name: "sipquest-agent-endpoint",
  compatibilityDate: "2025-12-01",
  entrypoint: "./workers/sipquest-agent-endpoint/src/index.js",
  observability: {
    enabled: true,
  },
  workersDev: true,
  env: {
    AGENT_ORIGIN_URL: bindings.text(process.env.AGENT_ORIGIN_URL ?? ""),
  },
});
