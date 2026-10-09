import { API, request } from "./api.js";

let editor = null;
let currentPage = null;
let autosaveTimer = null;

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[char]));

const siteSelect = (value = "uhrbv") => `
  <select name="site">
    <option value="uhrbv" ${value === "uhrbv" ? "selected" : ""}>UHR</option>
    <option value="ukrwerkspot" ${value === "ukrwerkspot" ? "selected" : ""}>Ukrwerkspot</option>
  </select>`;

const cmsNav = (site, active) => `
  <nav class="cms-subnav">
    ${[
      ["pages", "Сторінки"], ["menu", "Меню"], ["news", "Новини"],
      ["blog", "Блог"], ["catalog", "Каталог"], ["media", "Медіа"],
    ].map(([id, label]) =>
      `<a class="${active === id ? "active" : ""}" href="#cms/${id}/${site}">${label}</a>`
    ).join("")}
  </nav>`;

export async function renderCms(section = "pages", site = "uhrbv", id = "") {
  if (section === "page" && site) return pageEditor(Number(site));
  if (section === "menu") return menuEditor(site, id || "header");
  if (section === "news" || section === "blog") return postsEditor(site, section);
  if (section === "catalog") return catalogEditor(site);
  if (section === "media") return mediaEditor(site);
  return pagesEditor(site || "uhrbv");
}

async function pagesEditor(site) {
  const pages = await request(`/admin/cms/pages?site=${encodeURIComponent(site)}`);
  return `
    <h1>Редактор сайтів</h1>
    ${cmsNav(site, "pages")}
    <div class="cms-toolbar">
      <label>Сайт ${siteSelect(site)}</label>
      <div class="actions">${pages.length ? "" : `<button class="btn light" data-cms-bootstrap="${site}">Створити базові сторінки</button>`}
      <button class="btn" data-cms-new-page>Нова сторінка</button></div>
    </div>
    <div class="card table-scroll"><table>
      <thead><tr><th>Сторінка</th><th>URL</th><th>Чернетка</th><th>Опубліковано</th><th></th></tr></thead>
      <tbody>${pages.map((page) => `<tr>
        <td><strong>${esc(page.title)}</strong></td>
        <td>/${esc(page.slug === "home" ? "" : page.slug)}</td>
        <td>${page.draft_version_id ? "Так" : "—"}</td>
        <td>${page.published_version_id ? "Так" : "—"}</td>
        <td><a class="btn light" href="#cms/page/${page.id}">Відкрити редактор</a></td>
      </tr>`).join("") || `<tr><td colspan="5">Сторінок ще немає.</td></tr>`}</tbody>
    </table></div>
    <form id="cms-new-page-form" class="card cms-dialog" hidden>
      <h3>Нова сторінка</h3>
      <div class="fields">
        <label><span>Сайт</span>${siteSelect(site)}</label>
        <label><span>Мова</span><input name="locale" value="${site === "uhrbv" ? "nl" : "uk"}" required></label>
        <label><span>Назва</span><input name="title" required></label>
        <label><span>Slug</span><input name="slug" placeholder="about" pattern="[a-z0-9][a-z0-9/-]*" required></label>
      </div>
      <button class="btn">Створити</button>
    </form>`;
}

async function pageEditor(pageId) {
  currentPage = await request(`/admin/cms/pages/${pageId}`);
  const versions = currentPage.versions || [];
  return `
    <div class="cms-editor-head">
      <div><a href="#cms/pages/${currentPage.site}" class="back-link">← До сторінок</a>
        <h1>${esc(currentPage.title)}</h1><span class="muted">/${esc(currentPage.slug)}</span>
      </div>
      <div class="actions">
        <button class="btn light" data-cms-save>Зберегти чернетку</button>
        <button class="btn" data-cms-publish>Опублікувати</button>
      </div>
    </div>
    <div class="cms-meta card">
      <label>Назва<input id="cms-title" value="${esc(currentPage.title)}"></label>
      <label>SEO title<input id="cms-seo-title" value="${esc(currentPage.seo_title)}"></label>
      <label>SEO description<input id="cms-seo-description" value="${esc(currentPage.seo_description)}"></label>
    </div>
    <div id="gjs" class="cms-canvas">${window.grapesjs ? "" : "GrapesJS ще не зібрано на сервері."}</div>
    <details class="card cms-versions"><summary>Історія версій (${versions.length})</summary>
      ${versions.map((version) => `<div class="cms-version">
        <span>v${version.version} · ${new Date(version.created_at).toLocaleString("uk-UA")}</span>
        <button class="btn light" data-cms-rollback="${version.id}">Відновити</button>
      </div>`).join("")}
    </details>`;
}

async function menuEditor(site, area) {
  const menu = await request(`/admin/cms/menus/${site}/${area}`);
  return `
    <h1>Редактор меню</h1>${cmsNav(site, "menu")}
    <div class="cms-subnav"><a class="${area === "header" ? "active" : ""}" href="#cms/menu/${site}/header">Header</a>
      <a class="${area === "footer" ? "active" : ""}" href="#cms/menu/${site}/footer">Footer</a></div>
    <div class="cms-toolbar"><label>Сайт ${siteSelect(site)}</label>
      <button class="btn light" data-menu-add>Додати пункт</button>
      <button class="btn" data-menu-publish>Опублікувати меню</button></div>
    <form id="cms-menu-form" class="card" data-site="${site}" data-area="${area}">
      <div id="cms-menu-items">${(menu.draft_items || []).map(menuRow).join("")}</div>
      <button class="btn">Зберегти чернетку</button>
    </form>`;
}

function menuRow(item = { label: "", url: "/" }) {
  return `<div class="cms-menu-row">
    <input name="label" value="${esc(item.label)}" placeholder="Назва">
    <input name="url" value="${esc(item.url)}" placeholder="/about">
    <label class="check"><input name="visible" type="checkbox" ${item.visible !== false ? "checked" : ""}>Показувати</label>
    <button type="button" class="btn light" data-menu-up>↑</button>
    <button type="button" class="btn light" data-menu-down>↓</button>
    <button type="button" class="btn light" data-menu-remove>Видалити</button>
  </div>`;
}

async function postsEditor(site, kind) {
  const posts = await request(`/admin/cms/posts?site=${site}&kind=${kind}`);
  return `
    <h1>${kind === "news" ? "Новини" : "Блог"}</h1>${cmsNav(site, kind)}
    <div class="cms-toolbar"><label>Сайт ${siteSelect(site)}</label></div>
    <form id="cms-post-form" class="card" data-kind="${kind}">
      <div class="fields">
        <label><span>Сайт</span>${siteSelect(site)}</label>
        <label><span>Slug</span><input name="slug" required pattern="[a-z0-9][a-z0-9/-]*"></label>
        <label class="full"><span>Заголовок</span><input name="title" required></label>
        <label class="full"><span>Короткий опис</span><textarea name="excerpt"></textarea></label>
        <label class="full"><span>Обкладинка URL</span><input name="cover_url"></label>
        <label class="full"><span>Текст</span><textarea name="body" rows="12"></textarea></label>
      </div>
      <button class="btn">Зберегти чернетку</button>
    </form>
    <div class="card table-scroll"><table><thead><tr><th>Назва</th><th>Slug</th><th>Статус</th><th></th></tr></thead>
      <tbody>${posts.map((post) => `<tr><td>${esc(post.title)}</td><td>${esc(post.slug)}</td>
        <td><span class="badge">${esc(post.status)}</span></td>
        <td><button class="btn light" data-post-publish="${post.id}">Опублікувати</button></td></tr>`).join("")}</tbody>
    </table></div>`;
}

async function catalogEditor(site) {
  const categories = await request(`/admin/cms/categories?site=${site}`);
  return `
    <h1>Розділи каталогу</h1>${cmsNav(site, "catalog")}
    <div class="cms-toolbar"><label>Сайт ${siteSelect(site)}</label></div>
    <form id="cms-category-form" class="card">
      <div class="fields">
        <label><span>Сайт</span>${siteSelect(site)}</label>
        <label><span>Slug</span><input name="slug" required></label>
        <label><span>Назва</span><input name="title" required></label>
        <label><span>Професія в анкеті</span><input name="profession"></label>
        <label class="full"><span>Опис</span><textarea name="description"></textarea></label>
        <label><span>Зображення URL</span><input name="image_url"></label>
        <label><span>Порядок</span><input name="sort_order" type="number" value="0"></label>
      </div><button class="btn">Зберегти розділ</button>
    </form>
    <div class="grid">${categories.map((item) => `<article class="card"><h3>${esc(item.title)}</h3>
      <p>${esc(item.profession || "Усі професії")}</p><span class="muted">/${esc(item.slug)}</span></article>`).join("")}</div>`;
}

async function mediaEditor(site) {
  const media = await request(`/admin/cms/media?site=${site}`);
  return `
    <h1>Медіа-бібліотека</h1>${cmsNav(site, "media")}
    <div class="cms-toolbar"><label>Сайт ${siteSelect(site)}</label></div>
    <form id="cms-media-form" class="card" enctype="multipart/form-data">
      <input type="hidden" name="site" value="${site}">
      <div class="fields"><label><span>Файл</span><input name="file" type="file" accept="image/jpeg,image/png,image/webp,image/gif" required></label>
      <label><span>Alt-текст</span><input name="alt"></label></div><button class="btn">Завантажити</button>
    </form>
    <div class="cms-media-grid">${media.map((item) => `<figure class="card"><img src="${esc(item.url)}" alt="${esc(item.alt)}">
      <figcaption>${esc(item.name)}</figcaption></figure>`).join("")}</div>`;
}

export async function mountCms(section) {
  clearTimeout(autosaveTimer);
  if (section !== "page" || !currentPage || !window.grapesjs) return;
  editor?.destroy();
  editor = window.grapesjs.init({
    container: "#gjs",
    height: "70vh",
    fromElement: false,
    storageManager: false,
    selectorManager: { componentFirst: true },
    canvas: { styles: ["/admin/assets/styles.css", "/admin/assets/contrast.css"] },
    assetManager: { upload: false },
    deviceManager: { devices: [
      { id: "desktop", name: "Desktop", width: "" },
      { id: "tablet", name: "Tablet", width: "768px" },
      { id: "mobile", name: "Mobile", width: "375px" },
    ] },
  });
  registerBlocks(editor);
  if (currentPage.draft?.project_data && Object.keys(currentPage.draft.project_data).length) {
    editor.loadProjectData(currentPage.draft.project_data);
  } else if (currentPage.draft?.html) {
    editor.setComponents(currentPage.draft.html);
    editor.setStyle(currentPage.draft.css || "");
  }
  editor.on("update", () => {
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => saveCurrentPage(true), 30000);
  });
}

function registerBlocks(instance) {
  const blocks = [
    ["heading", "Заголовок", `<h2>Новий заголовок</h2>`],
    ["text", "Текст", `<p>Натисніть двічі, щоб змінити текст.</p>`],
    ["image", "Зображення", `<img src="https://placehold.co/1200x600" alt="">`],
    ["hero", "Hero", `<section class="hero"><div><div class="eyebrow">Надзаголовок</div><h1>Головний заголовок</h1><p>Опис сторінки.</p><a class="btn" href="#">Детальніше</a></div></section>`],
    ["columns", "2 колонки", `<section class="section"><div class="grid"><div class="card"><h3>Колонка 1</h3><p>Текст</p></div><div class="card"><h3>Колонка 2</h3><p>Текст</p></div></div></section>`],
    ["cta", "Заклик", `<section class="callout"><div><h2>Готові почати?</h2><p>Зв'яжіться з нами.</p></div><a class="btn lime" href="#">Почати</a></section>`],
    ["faq", "FAQ", `<section class="section"><h2>Питання та відповіді</h2><details><summary>Питання</summary><p>Відповідь</p></details></section>`],
    ["catalog", "Каталог", `<section data-cms-widget="catalog"><h2>Каталог фахівців</h2><div data-widget-content>Завантаження…</div></section>`],
    ["registration", "Форма реєстрації", `<section data-cms-widget="registration"><h2>Реєстрація</h2><div data-widget-content>Завантаження…</div></section>`],
    ["news", "Новини", `<section data-cms-widget="posts" data-kind="news" data-limit="3"><h2>Новини</h2><div data-widget-content>Завантаження…</div></section>`],
    ["blog", "Блог", `<section data-cms-widget="posts" data-kind="blog" data-limit="3"><h2>Блог</h2><div data-widget-content>Завантаження…</div></section>`],
  ];
  blocks.forEach(([id, label, content]) => instance.BlockManager.add(id, { label, category: "UHR", content }));
}

async function saveCurrentPage(silent = false) {
  if (!editor || !currentPage) return;
  const payload = {
    title: document.querySelector("#cms-title")?.value || currentPage.title,
    seo_title: document.querySelector("#cms-seo-title")?.value || "",
    seo_description: document.querySelector("#cms-seo-description")?.value || "",
    project_data: editor.getProjectData(),
    html: editor.getHtml(),
    css: editor.getCss(),
    note: silent ? "Автозбереження" : "Ручне збереження",
    expected_version: currentPage.draft?.version ?? null,
  };
  currentPage = await request(`/admin/cms/pages/${currentPage.id}/draft`, { method: "PUT", json: payload });
  if (!silent) window.dispatchEvent(new CustomEvent("cms-toast", { detail: "Чернетку збережено." }));
}

export async function handleCmsSubmit(form) {
  if (form.id === "cms-new-page-form") {
    const data = Object.fromEntries(new FormData(form));
    const page = await request("/admin/cms/pages", { method: "POST", json: data });
    location.hash = `cms/page/${page.id}`;
    return true;
  }
  if (form.id === "cms-menu-form") {
    const rows = [...form.querySelectorAll(".cms-menu-row")];
    const items = rows.map((row) => ({
      label: row.querySelector('[name="label"]').value,
      url: row.querySelector('[name="url"]').value,
      visible: row.querySelector('[name="visible"]').checked,
    }));
    await request(`/admin/cms/menus/${form.dataset.site}/${form.dataset.area}`, { method: "PUT", json: { items } });
    return true;
  }
  if (form.id === "cms-post-form") {
    const data = Object.fromEntries(new FormData(form));
    data.kind = form.dataset.kind;
    await request("/admin/cms/posts", { method: "POST", json: data });
    return true;
  }
  if (form.id === "cms-category-form") {
    const data = Object.fromEntries(new FormData(form));
    data.sort_order = Number(data.sort_order || 0);
    data.is_visible = true;
    await request("/admin/cms/categories", { method: "POST", json: data });
    return true;
  }
  if (form.id === "cms-media-form") {
    const response = await fetch(`${API}/admin/cms/media`, { method: "POST", credentials: "include", body: new FormData(form) });
    if (!response.ok) throw new Error("Не вдалося завантажити файл");
    return true;
  }
  return false;
}

export async function handleCmsClick(target) {
  const bootstrap = target.closest("[data-cms-bootstrap]");
  if (bootstrap) {
    await request(`/admin/cms/pages/bootstrap/${bootstrap.dataset.cmsBootstrap}`, { method: "POST", json: {} });
    location.hash = `cms/pages/${bootstrap.dataset.cmsBootstrap}`;
    location.reload();
    return true;
  }
  if (target.closest("[data-cms-new-page]")) {
    document.querySelector("#cms-new-page-form").hidden = false;
    return true;
  }
  if (target.closest("[data-cms-save]")) {
    await saveCurrentPage(false);
    return true;
  }
  if (target.closest("[data-cms-publish]")) {
    await saveCurrentPage(true);
    await request(`/admin/cms/pages/${currentPage.id}/publish`, { method: "POST", json: {} });
    window.dispatchEvent(new CustomEvent("cms-toast", { detail: "Сторінку опубліковано." }));
    return true;
  }
  const rollback = target.closest("[data-cms-rollback]");
  if (rollback) {
    await request(`/admin/cms/pages/${currentPage.id}/rollback/${rollback.dataset.cmsRollback}`, { method: "POST", json: {} });
    location.reload();
    return true;
  }
  const add = target.closest("[data-menu-add]");
  if (add) {
    document.querySelector("#cms-menu-items").insertAdjacentHTML("beforeend", menuRow());
    return true;
  }
  const rowAction = target.closest("[data-menu-up],[data-menu-down],[data-menu-remove]");
  if (rowAction) {
    const row = rowAction.closest(".cms-menu-row");
    if (rowAction.hasAttribute("data-menu-remove")) row.remove();
    else if (rowAction.hasAttribute("data-menu-up") && row.previousElementSibling) row.before(row.previousElementSibling);
    else if (rowAction.hasAttribute("data-menu-down") && row.nextElementSibling) row.after(row.nextElementSibling);
    return true;
  }
  const menuPublish = target.closest("[data-menu-publish]");
  if (menuPublish) {
    const form = document.querySelector("#cms-menu-form");
    await handleCmsSubmit(form);
    await request(`/admin/cms/menus/${form.dataset.site}/${form.dataset.area}/publish`, { method: "POST", json: {} });
    return true;
  }
  const postPublish = target.closest("[data-post-publish]");
  if (postPublish) {
    await request(`/admin/cms/posts/${postPublish.dataset.postPublish}/publish`, { method: "POST", json: {} });
    return true;
  }
  return false;
}

export function handleCmsChange(select) {
  if (select.name !== "site") return false;
  const [root, section = "pages", , detail] = (location.hash.slice(1) || "cms/pages").split("/");
  if (root !== "cms") return false;
  location.hash = `cms/${section}/${select.value}${detail ? `/${detail}` : ""}`;
  return true;
}
