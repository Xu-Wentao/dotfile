/// <reference path="../env.d.ts" />

function getBridgeConfig() {
  const baseURL = process.env.SUPER_AGENT_TOOLS_BRIDGE_URL?.trim()
  const token = process.env.SUPER_AGENT_TOOLS_BRIDGE_TOKEN?.trim()

  if (!baseURL || !token) {
    throw new Error("Missing tools auth bridge configuration")
  }

  return { baseURL: baseURL.replace(/\/$/, ""), token }
}

async function postBridge(path: string, body: Record<string, unknown>, signal?: AbortSignal) {
  const bridge = getBridgeConfig()
  return fetch(`${bridge.baseURL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${bridge.token}`,
    },
    body: JSON.stringify(body),
    signal,
  })
}

export async function postImageRead(body: Record<string, unknown>) {
  return postBridge("/image-read", body)
}

export async function postBaiduSearch(body: Record<string, unknown>, signal?: AbortSignal) {
  return postBridge("/baidu-search", body, signal)
}
