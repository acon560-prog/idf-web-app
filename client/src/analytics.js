const GA_ID = (process.env.REACT_APP_GA4_MEASUREMENT_ID || "").trim();

let gaInitialized = false;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.async = true;
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

export async function initAnalytics() {
  if (!GA_ID || gaInitialized || typeof window === "undefined") return;

  await loadScript(`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`);

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() {
    window.dataLayer.push(arguments);
  };

  window.gtag("js", new Date());
  // Disable automatic first pageview so SPA tracking is controlled by route changes.
  window.gtag("config", GA_ID, { send_page_view: false });

  gaInitialized = true;
}

export function trackPageView(path) {
  if (!GA_ID || typeof window === "undefined" || typeof window.gtag !== "function") return;

  window.gtag("event", "page_view", {
    page_path: path,
    page_location: `${window.location.origin}${path}`,
    page_title: document.title,
  });
}