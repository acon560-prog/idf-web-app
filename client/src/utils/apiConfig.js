const DEFAULT_API_BASE_URL = "https://idf-web-app.onrender.com/api";
const envBase = (
  process.env.REACT_APP_API_BASE_URL || DEFAULT_API_BASE_URL
).trim();

function getWindowOrigin() {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin.replace(/\/$/, "");
  }
  return "";
}

let cachedBaseUrl;

export function getApiBaseUrl() {
  if (cachedBaseUrl) {
    return cachedBaseUrl;
  }

  if (envBase) {
    cachedBaseUrl = envBase.replace(/\/$/, "");
    return cachedBaseUrl;
  }

  const origin = getWindowOrigin();
  if (origin) {
    cachedBaseUrl = `${origin}/api`;
    return cachedBaseUrl;
  }

  cachedBaseUrl = "/api";
  return cachedBaseUrl;
}

export function getApiRootUrl() {
  const base = getApiBaseUrl();
  if (base.endsWith("/api")) {
    return base.slice(0, -4);
  }
  return base;
}

export function buildApiUrl(path = "") {
  const base = getApiBaseUrl();
  if (!path) {
    return base;
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

export async function readJsonResponse(
  response,
  contextMessage = "Request failed.",
) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const text = await response.text();
    const snippet = text.slice(0, 140).replace(/\s+/g, " ").trim();
    const preview = snippet ? ` Preview: ${snippet}` : "";
    throw new Error(
      `${contextMessage} Server responded with unexpected content.${preview}`,
    );
  }

  try {
    return await response.json();
  } catch (error) {
    console.error("Failed to parse JSON response", error);
    throw new Error(`${contextMessage} Unable to parse server response.`);
  }
}
