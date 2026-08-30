const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // response wasn't JSON -- keep statusText
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

export function getHealth() {
  return request("/api/health");
}

export function getDataQuality() {
  return request("/api/data-quality");
}

export function refreshData() {
  return request("/api/data-refresh", { method: "POST" });
}

export function sendChatMessage(message, sessionId) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

export function resetSession(sessionId) {
  if (!sessionId) return Promise.resolve();
  return request(`/api/session/${sessionId}/reset`, { method: "POST" });
}
