const API = "/api/v1/public/cms";

function siteId() {
  return document.body.dataset.site === "ukr" || location.hostname.includes("ukrwerkspot")
    ? "ukrwerkspot"
    : "uhrbv";
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

async function json(url) {
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}

async function renderMenu(site, area = "header") {
  const data = await json(`${API}/menus/${site}/${area}`).catch(() => ({ items: [] }));
  const visible = (data.items || []).filter((item) => item.visible !== false);
  if (!visible.length) return "";
  return `<nav class="cms-public-menu cms-public-menu-${area}" aria-label="${area} navigation">${visible
    .map((item) => `<a href="${escapeHtml(item.url || "/")}">${escapeHtml(item.label)}</a>`)
    .join("")}</nav>`;
}

async function hydratePosts(element, site) {
  const kind = element.dataset.kind || "blog";
  const limit = Number(element.dataset.limit || 3);
  const posts = await json(`${API}/posts/${site}?kind=${encodeURIComponent(kind)}&limit=${limit}`);
  const target = element.querySelector("[data-widget-content]") || element;
  target.innerHTML = `<div class="grid">${posts.map((post) => `<article class="card">
    ${post.cover_url ? `<img src="${escapeHtml(post.cover_url)}" alt="">` : ""}
    <h3>${escapeHtml(post.title)}</h3><p>${escapeHtml(post.excerpt)}</p>
    <a href="/${kind}/${escapeHtml(post.slug)}">Детальніше →</a>
  </article>`).join("")}</div>`;
}

async function hydrateCatalog(element, site) {
  const data = await json(`${API}/catalog/${site}`);
  const target = element.querySelector("[data-widget-content]") || element;
  target.innerHTML = `<div class="cards worker-list">${data.workers.map((worker) => `<article class="card">
    <span class="muted">Профіль #${worker.id}</span>
    <h3>${escapeHtml(worker.profession)}</h3>
    <p>${escapeHtml(worker.city)} · ${worker.experience_years || "—"} років досвіду</p>
    <p>${escapeHtml(worker.description)}</p>
  </article>`).join("") || `<div class="card">Профілі готуються до публікації.</div>`}</div>`;
}

function hydrateRegistration(element, site) {
  const target = element.querySelector("[data-widget-content]") || element;
  const uk = site === "ukrwerkspot";
  target.innerHTML = `<form class="card cms-registration-form">
    <div class="fields">
      ${uk
        ? `<label><span>Ім’я</span><input name="name" required></label>
           <label><span>Професія</span><input name="profession" required></label>`
        : `<label><span>Bedrijfsnaam</span><input name="company_name" required></label>
           <label><span>Contactpersoon</span><input name="contact_name" required></label>`}
      <label><span>Email</span><input name="email" type="email" required></label>
      <label><span>${uk ? "Телефон" : "Telefoon"}</span><input name="phone" type="tel" required></label>
    </div>
    <button class="btn" type="submit">${uk ? "Надіслати" : "Aanmelden"}</button>
    <p data-form-status role="status"></p>
  </form>`;
  const form = target.querySelector("form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form));
    const path = uk ? "craftsmen" : "companies";
    const response = await fetch(`/api/v1/public/applications/${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    const status = form.querySelector("[data-form-status]");
    status.textContent = response.ok
      ? (uk ? "Дякуємо! Анкету надіслано." : "Bedankt! Uw registratie is ontvangen.")
      : (uk ? "Не вдалося надіслати анкету." : "Verzenden is niet gelukt.");
    if (response.ok) form.reset();
  });
}

async function hydrateWidgets(root, site) {
  const widgets = [...root.querySelectorAll("[data-cms-widget]")];
  await Promise.all(widgets.map(async (element) => {
    try {
      if (element.dataset.cmsWidget === "posts") await hydratePosts(element, site);
      if (element.dataset.cmsWidget === "catalog") await hydrateCatalog(element, site);
      if (element.dataset.cmsWidget === "registration") hydrateRegistration(element, site);
    } catch {
      const target = element.querySelector("[data-widget-content]") || element;
      target.textContent = "Не вдалося завантажити дані.";
    }
  }));
}

async function renderPost(site, kind, slug) {
  const post = await json(`${API}/posts/${site}/${kind}/${slug}`);
  const app = document.querySelector("#app");
  const menu = await renderMenu(site);
  const footer = await renderMenu(site, "footer");
  app.innerHTML = `<div class="wrap">${menu}<main class="legal">
    <a href="/${kind}">← Назад</a><h1>${escapeHtml(post.title)}</h1>
    <p class="muted">${post.published_at ? new Date(post.published_at).toLocaleDateString() : ""}</p>
    ${post.cover_url ? `<img class="portfolio" src="${escapeHtml(post.cover_url)}" alt="">` : ""}
    <article>${post.body}</article>
  </main>${footer}</div>`;
  document.title = post.title;
  return true;
}

export async function renderCmsPage() {
  const site = siteId();
  const parts = location.pathname.replace(/^\/|\/$/g, "").split("/").filter(Boolean);
  if ((parts[0] === "blog" || parts[0] === "news") && parts[1]) {
    try {
      return await renderPost(site, parts[0], parts.slice(1).join("/"));
    } catch {
      return false;
    }
  }
  const slug = parts.join("/") || "home";
  try {
    const page = await json(`${API}/pages/${site}/${encodeURIComponent(slug)}`);
    const app = document.querySelector("#app");
    const menu = await renderMenu(site);
    const footer = await renderMenu(site, "footer");
    const style = document.createElement("style");
    style.dataset.cmsPage = String(page.id);
    style.textContent = page.css || "";
    document.head.append(style);
    app.innerHTML = `<div class="wrap">${menu}</div><main class="cms-page">${page.html}</main><div class="wrap">${footer}</div>`;
    document.title = page.seo_title || page.title;
    const meta = document.querySelector('meta[name="description"]') || document.head.appendChild(document.createElement("meta"));
    meta.name = "description";
    meta.content = page.seo_description || "";
    await hydrateWidgets(app, site);
    return true;
  } catch {
    return false;
  }
}
