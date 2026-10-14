export const ADMIN_BASE = "/admin";

export function adminHref(path = "") {
  const raw = String(path).replace(/^#/, "");
  const splitAt = raw.indexOf("?");
  const pathname = (splitAt === -1 ? raw : raw.slice(0, splitAt)).replace(/^\/+/, "");
  const query = splitAt === -1 ? "" : raw.slice(splitAt);
  return `${ADMIN_BASE}/${pathname}${query}`;
}

export function adminRoute() {
  let path = location.pathname;
  if (path === ADMIN_BASE || path === `${ADMIN_BASE}/`) return ["overview"];
  if (path.startsWith(`${ADMIN_BASE}/`)) path = path.slice(ADMIN_BASE.length + 1);
  else path = path.replace(/^\/+/, "");
  const clean = path.replace(/\/+$/, "");
  return clean ? clean.split("/") : ["overview"];
}

export function adminSearch() {
  return new URLSearchParams(location.search);
}

export function navigate(path) {
  const next = adminHref(path);
  if (next !== location.pathname + location.search) history.pushState(null, "", next);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function adoptLegacyHash() {
  const hash = location.hash.replace(/^#\/?/, "");
  if (!hash || hash === "logout") {
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    return;
  }
  history.replaceState(null, "", adminHref(hash));
}
