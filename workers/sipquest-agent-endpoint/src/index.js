const json = (body, status = 200, headers = {}) =>
  new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...headers,
    },
  });

const normalizeOrigin = (value) => {
  const origin = (value || "").trim().replace(/\/+$/, "");
  if (!origin) {
    return "";
  }

  try {
    const url = new URL(origin);
    if (url.protocol !== "https:") {
      return "";
    }
    return url.origin + url.pathname.replace(/\/+$/, "");
  } catch {
    return "";
  }
};

const proxyToAgent = async (request, env) => {
  const origin = normalizeOrigin(env.AGENT_ORIGIN_URL);
  if (!origin) {
    return json(
      {
        ok: false,
        error: "AGENT_ORIGIN_URL is not configured.",
        expected: "Set AGENT_ORIGIN_URL to the public HTTPS origin running the SipQuest uAgent, without /submit.",
      },
      503,
    );
  }

  const incomingUrl = new URL(request.url);
  const target = new URL(incomingUrl.pathname + incomingUrl.search, origin);
  const headers = new Headers(request.headers);
  headers.set("x-forwarded-host", incomingUrl.host);
  headers.set("x-forwarded-proto", incomingUrl.protocol.replace(":", ""));

  return fetch(target, {
    method: request.method,
    headers,
    body: request.body,
    redirect: "manual",
  });
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET,POST,OPTIONS",
          "access-control-allow-headers": "content-type,authorization",
          "access-control-max-age": "86400",
        },
      });
    }

    if (url.pathname === "/" || url.pathname === "/health") {
      return json({
        ok: true,
        service: "sipquest-agent-endpoint",
        submit: `${url.origin}/submit`,
        agentOriginConfigured: Boolean(normalizeOrigin(env.AGENT_ORIGIN_URL)),
      });
    }

    if (url.pathname === "/submit") {
      return proxyToAgent(request, env);
    }

    return json({ ok: false, error: "Not found" }, 404);
  },
};
