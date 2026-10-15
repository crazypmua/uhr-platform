import { request } from "./api.js";
import { handleCmsChange, handleCmsClick, handleCmsSubmit, mountCms, renderCms } from "./cms.js";
import { ICONS } from "./icons.js";
import { adminHref, adminRoute, adminSearch, adoptLegacyHash, navigate } from "./path.js";

const app = document.querySelector("#app");
const state = { user: null, toast: "", openAnketa: "" };

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));

const icon = (name) => `<i data-lucide="${name}" aria-hidden="true"></i>`;
const icons = () => window.lucide?.createIcons({ attrs: { "stroke-width": 1.7, "aria-hidden": "true" } });
const route = adminRoute;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("uk-UA") : "—");
const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleString("uk-UA", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";
const PAGE_SIZE = 10;
const badgeClass = (status) => (status === "approved" || status === "confirmed" || status === "done" ? "" : "yellow");

const NAV = [
  ["overview", ICONS.overview, "Огляд"],
  ["masters", ICONS.masters, "Анкети майстрів"],
  ["companies", ICONS.companies, "Компанії"],
  ["requests", ICONS.requests, "Заявки"],
  ["messages", ICONS.messages, "Повідомлення"],
  ["cms", ICONS.siteEditor, "Редактор сайтів"],
  ["settings", ICONS.settings, "Налаштування"],
];

function shell(content, page) {
  const link = ([id, name, label]) =>
    `<a class="${page === id ? "active" : ""}" ${page === id ? 'aria-current="page"' : ""} href="${adminHref(id)}">${icon(name)}<span>${label}</span></a>`;
  const name = state.user?.name || "Менеджер";
  return `<div class="admin-layout">
    <aside class="admin-sidebar">
      <a href="${adminHref("overview")}" class="admin-brand"><span class="admin-mark">U</span><span>UHR</span></a>
      <div class="admin-nav-label">Робочий простір</div>
      <nav class="admin-nav" aria-label="Меню">${NAV.map(link).join("")}</nav>
      <div class="admin-account">
        <span class="admin-avatar">${esc(name.trim().charAt(0).toUpperCase())}</span>
        <div>
          <strong>${esc(name)}</strong>
          <span>${esc(state.user?.email || "")}</span>
          <a href="${adminHref("overview")}" data-logout>Вийти</a>
        </div>
      </div>
    </aside>
    <main class="content admin-main">${content}</main>
  </div>`;
}

function paint(content, page) {
  const layout = document.querySelector(".admin-layout");
  const main = layout?.querySelector(".admin-main");
  if (!layout || !main) {
    app.innerHTML = shell(content, page);
    return;
  }
  main.innerHTML = content;
  if (page !== "messages") window.scrollTo(0, 0);
  layout.querySelectorAll(".admin-nav a").forEach((link) => {
    const active = link.getAttribute("href") === adminHref(page);
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

function pageParams() {
  return adminSearch();
}

function currentPage() {
  const value = Number(pageParams().get("page") || 1);
  return Number.isInteger(value) && value > 0 ? value : 1;
}

function pageHref(path, page, extra = {}) {
  const params = new URLSearchParams();
  Object.entries(extra).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return adminHref(`${path}${query ? `?${query}` : ""}`);
}

function slicePage(items) {
  const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE) || 1);
  const page = Math.min(currentPage(), pages);
  const start = (page - 1) * PAGE_SIZE;
  return { page, pages, total: items.length, rows: items.slice(start, start + PAGE_SIZE), start };
}

function pageNote(meta) {
  if (!meta.total) return "";
  const from = meta.start + 1;
  const to = meta.start + meta.rows.length;
  return `<p class="admin-count">${from}–${to} з ${meta.total}</p>`;
}

function pager(path, meta, extra = {}) {
  if (meta.pages < 2) return "";
  const item = (n, label, current = false) =>
    current
      ? `<span class="admin-page is-current" aria-current="page">${label}</span>`
      : `<a class="admin-page" href="${pageHref(path, n, extra)}">${label}</a>`;
  const links = [];
  for (let n = 1; n <= meta.pages; n += 1) links.push(item(n, String(n), n === meta.page));
  const prev = meta.page > 1 ? item(meta.page - 1, "Назад") : `<span class="admin-page is-disabled">Назад</span>`;
  const next = meta.page < meta.pages ? item(meta.page + 1, "Далі") : `<span class="admin-page is-disabled">Далі</span>`;
  return `<nav class="admin-pager" aria-label="Сторінки">${prev}${links.join("")}${next}</nav>`;
}

function rowActions(href, api, id, label) {
  return `<div class="admin-actions">
    <a class="admin-icon-btn" href="${href}" aria-label="Редагувати">${icon(ICONS.edit)}</a>
    <button class="admin-icon-btn is-danger" type="button" data-delete="${api}" data-id="${id}" data-label="${esc(label)}" aria-label="Видалити">${icon(ICONS.trash)}</button>
  </div>`;
}

function toast(text) {
  document.querySelector(".toast")?.remove();
  const el = document.createElement("div");
  el.className = "toast";
  el.setAttribute("role", "status");
  el.textContent = text;
  document.body.append(el);
  setTimeout(() => el.remove(), 4000);
}

function loginPage(error = "") {
  return `<div class="wizard"><div class="card">
    <div class="eyebrow">UHR · Ukrwerkspot</div>
    <h1>Вхід</h1>
    <p>Увійдіть, щоб перевіряти анкети, заявки компаній і тексти сайтів.</p>
    ${error ? `<div class="note">${esc(error)}</div>` : ""}
    <form id="login-form">
      <div class="fields">
        <label><span>Email</span><input name="email" type="email" required autocomplete="username"></label>
        <label><span>Пароль</span><input name="password" type="password" required autocomplete="current-password"></label>
      </div>
      <button class="btn" style="margin-top:25px">Увійти →</button>
    </form>
    <p style="margin-top:22px"><a href="/">← На сайт</a></p>
  </div></div>`;
}

function statusFilter(current, section, extra = []) {
  const options = [["", "Усі статуси"], ["pending", "На перевірці"], ["clarification", "Уточнення"], ["approved", "Схвалено"], ["rejected", "Відхилено"], ...extra];
  return `<select id="status-filter" class="admin-filter" data-section="${section}">${options
    .map(([value, label]) => `<option value="${value}" ${current === value ? "selected" : ""}>${label}</option>`)
    .join("")}</select>`;
}

function pageHead(title, text, tools = "") {
  return `<header class="admin-head"><div class="admin-head-title"><h1>${title}</h1>${text ? `<p>${text}</p>` : ""}</div>${
    tools ? `<div class="admin-head-tools">${tools}</div>` : ""
  }</header>`;
}

function listFoot(path, meta, extra) {
  if (!meta.total) return "";
  return `<footer class="admin-list-foot">${pageNote(meta)}${pager(path, meta, extra)}</footer>`;
}

async function overview() {
  const data = await request("/admin/overview");
  const cards = [
    ["Нові анкети", data.new_masters, adminHref("masters"), "Перевірка VCA та професійного досвіду."],
    ["Компанії на перевірці", data.companies_review, adminHref("companies"), "Перевірка юридичних даних та документів."],
    ["Активні заявки", data.active_requests, adminHref("requests"), "Планування та узгодження з компаніями."],
    ["Опубліковані профілі", data.published_profiles, adminHref("masters"), "Обезличені профілі для каталогу UHR."],
  ];
  return `${pageHead("Огляд", "Ukrwerkspot збирає анкети майстрів. UHR приймає компанії.")}
    <div class="admin-metrics">${cards
      .map(([label, value, href]) => `<a class="admin-metric" href="${href}"><span>${esc(label)}</span><strong>${esc(value)}</strong></a>`)
      .join("")}</div>
    <div class="admin-links">${cards
      .map(([, , href, text]) => `<a href="${href}">${esc(text)}</a>`)
      .join("")}</div>`;
}

async function siteSettings() {
  const sites = await request("/admin/sites");
  const cards = sites
    .map(
      (site) => `<form class="card site-settings-form" data-site="${esc(site.site)}">
        <div class="eyebrow">${esc(site.url)}</div>
        <h2>${esc(site.label)}</h2>
        <p>${
          site.is_open
            ? "Сайт відкритий: усі відвідувачі бачать повний інтерфейс."
            : "Сайт закритий: відвідувачі бачать сторінку очікування."
        }</p>
        <label class="check">
          <input name="is_open" type="checkbox" ${site.is_open ? "checked" : ""}>
          Відкрити повний сайт для всіх
        </label>
        <div class="actions" style="margin-top:24px">
          <button class="btn">Зберегти</button>
          <button class="btn light" type="button" data-preview-site="${esc(site.site)}">
            Переглянути повний сайт ↗
          </button>
        </div>
      </form>`
    )
    .join("");
  return `${pageHead("Налаштування", "У закритому режимі звичайний відвідувач бачить заглушку. Перегляд відкриває повний сайт тільки для адміністратора.")}
    <div class="admin-record"><div class="grid">${cards}</div>
    <div class="note">Доступ до закритого Ukrwerkspot передається окремою захищеною cookie на 1 годину, тому що браузер не дозволяє спільну cookie для двох різних доменів.</div></div>`;
}

function table(headers, rows) {
  if (!rows.length) return `<div class="admin-empty">Поки що немає записів.</div>`;
  return `<div class="admin-sheet"><table class="admin-table">
    <thead><tr>${headers.map((h) => `<th${h === "Дії" ? ' class="admin-actions-col"' : ""}>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.join("")}</tbody>
  </table></div>`;
}

async function masters() {
  const status = pageParams().get("status") || "";
  const items = await request("/admin/craftsmen" + (status ? `?status=${encodeURIComponent(status)}` : ""));
  const meta = slicePage(items);
  const rows = meta.rows.map(
    (item) => `<tr class="${item.status === "pending" || item.status === "clarification" ? "is-attention" : ""}">
      <td><a href="${adminHref(`masters/${item.id}`)}">#${item.id}</a></td>
      <td>${esc(item.name)}</td>
      <td>${esc(item.profession)}</td>
      <td>${esc(item.city)}</td>
      <td>${esc(item.source)}</td>
      <td><span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></td>
      <td>${fmtDate(item.created_at)}</td>
      <td>${rowActions(adminHref(`masters/${item.id}`), "craftsmen", item.id, item.name)}</td>
    </tr>`
  );
  return `${pageHead("Анкети майстрів", "Після схвалення публікується лише професійний профіль без імені та контактів.", statusFilter(status, "masters"))}${table(
    ["ID", "Ім’я", "Спеціалізація", "Місто", "Джерело", "Статус", "Дата", "Дії"],
    rows
  )}${listFoot("masters", meta, { status })}`;
}

function fieldList(pairs) {
  return `<div class="fields">${pairs
    .map(
      ([label, value]) =>
        `<label class="${String(value).length > 80 ? "full" : ""}"><span>${esc(label)}</span><div class="note" style="margin:0">${esc(value || "—")}</div></label>`
    )
    .join("")}</div>`;
}

function documentsBlock(documents = []) {
  if (!documents.length) return `<div class="card" style="margin:24px 0"><h3>Файли</h3><p>Файли не завантажено.</p></div>`;
  const groups = {};
  for (const doc of documents) (groups[doc.kind_label] ||= []).push(doc);
  return `<div class="card" style="margin:24px 0"><h3>Файли</h3>${Object.entries(groups)
    .map(
      ([label, docs]) => `<h4>${esc(label)}</h4><div class="admin-documents">${docs
        .map(
          (doc) => `<a class="admin-document" href="${esc(doc.url)}" target="_blank" rel="noopener">${
            doc.mime_type?.startsWith("image/") ? `<img src="${esc(doc.url)}" alt="" loading="lazy">` : icon(ICONS.document)
          }<span>${esc(doc.original_name)}</span></a>`
        )
        .join("")}</div>`
    )
    .join("")}</div>`;
}

function snaBlock(item) {
  const sna = item.sna_details || {};
  if (!sna.checked_at) return "";
  const register = sna.register;
  const extracted = sna.extracted || {};
  const verdict = item.sna_verified
    ? "Підтверджено реєстром SNA"
    : !sna.kvk_matches
      ? "KvK у сертифікаті не збігається з указаним компанією"
      : register?.found
        ? "Компанія є в реєстрі SNA, але KvK не прочитано з файлу — перевірте сертифікат вручну"
        : register?.found === false
          ? "KvK не знайдено в реєстрі SNA"
          : "Автоматично перевірити не вдалося — перевірте вручну";
  return `<div class="card" style="margin:24px 0">
    <h3>Сертифікат SNA</h3>
    <p><span class="badge ${item.sna_verified ? "" : "yellow"}">${esc(verdict)}</span></p>
    ${fieldList([
      ["KvK для перевірки", sna.kvk],
      ["З сертифіката: компанія", extracted.company_name],
      ["З сертифіката: місто", extracted.city],
      ["З сертифіката: KvK", extracted.kvk],
      ["З сертифіката: дата", extracted.date],
      ["Реєстр: компанія", register?.company_name],
      ["Реєстр: адреса", register?.address],
      ["Реєстр: діяльність", (register?.activities || []).join(", ")],
      ["Перевірено", fmtDate(sna.checked_at)],
    ])}
    <p style="margin-top:16px"><a href="${esc(sna.register_url)}" target="_blank" rel="noopener">Відкрити реєстр SNA ↗</a></p>
  </div>`;
}

function statusForm(prefix, item) {
  return `<form id="status-form" class="card" data-prefix="${prefix}" data-id="${item.id}">
    <h3>Рішення менеджера</h3>
    <p>Поточний статус: <span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></p>
    <label class="full"><span>Коментар для уточнення або відмови</span><textarea name="comment">${esc(item.admin_comment)}</textarea></label>
    <div class="actions" style="margin-top:20px">
      <button class="btn" data-status="approved" type="submit">Схвалити</button>
      <button class="btn light" data-status="clarification" type="submit">Уточнити</button>
      <button class="btn light" data-status="rejected" type="submit">Відхилити</button>
    </div>
  </form>`;
}

async function masterDetail(id) {
  const item = await request(`/admin/craftsmen/${id}`);
  return `<div class="admin-record"><a href="${adminHref("masters")}" class="back-link">${icon("arrow-left")} До анкет</a>
    <div class="eyebrow">Ukrwerkspot · анкета #${item.id}</div>
    <h1>${esc(item.name || "Без імені")}</h1>
    <p>${esc(item.profession)} · ${esc(item.city)} · ${esc(item.status_label)}</p>
    ${fieldList([
      ["Телефон", item.phone],
      ["Email", item.email],
      ["Перелік робіт", item.works],
      ["Досвід роботи в Україні", item.experience_ua],
      ["Досвід роботи в Нідерландах", item.experience_nl],
      ["Мова", item.language],
      ["Компанія", item.company_name],
      ["KVK", item.kvk],
      ["BTW", item.btw],
      ["Адреса", item.address],
      ["Сайт", item.website],
      ["Instagram", item.instagram],
      ["Facebook", item.facebook],
      ["TikTok", item.tiktok],
      ["Додаткові роботи", item.extra_work],
      ["Досвід, років", item.experience_years],
      ["Ставка €/год", item.hourly_rate],
      ["Радіус, км", item.radius_km],
      ["Доступність", item.availability],
      ["По всій країні", item.nationwide ? "Так" : "Ні"],
      ["Портфоліо", item.portfolio_url],
    ])}
    <div class="card" style="margin:24px 0"><h3>Опис досвіду</h3><p>${esc(item.description || "—")}</p></div>
    ${documentsBlock(item.documents)}
    ${statusForm("craftsmen", item)}</div>`;
}

async function companies() {
  const status = pageParams().get("status") || "";
  const items = await request("/admin/companies" + (status ? `?status=${encodeURIComponent(status)}` : ""));
  const meta = slicePage(items);
  const rows = meta.rows.map(
    (item) => `<tr class="${item.status === "pending" || item.status === "clarification" ? "is-attention" : ""}">
      <td><a href="${adminHref(`companies/${item.id}`)}">#${item.id}</a></td>
      <td>${esc(item.company_name)}</td>
      <td>${esc(item.contact_name)}</td>
      <td>${esc(item.source)}</td>
      <td><span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></td>
      <td>${fmtDate(item.created_at)}</td>
      <td>${rowActions(adminHref(`companies/${item.id}`), "companies", item.id, item.company_name)}</td>
    </tr>`
  );
  return `${pageHead("Компанії", "Реєстрації з uhrbv.nl. Після перевірки компанія отримає доступ до каталогу.", statusFilter(status, "companies"))}${table(
    ["ID", "Компанія", "Контакт", "Джерело", "Статус", "Дата", "Дії"],
    rows
  )}${listFoot("companies", meta, { status })}`;
}

async function companyDetail(id) {
  const item = await request(`/admin/companies/${id}`);
  return `<div class="admin-record"><a href="${adminHref("companies")}" class="back-link">${icon("arrow-left")} До компаній</a>
    <div class="eyebrow">UHR · компанія #${item.id}</div>
    <h1>${esc(item.company_name)}</h1>
    ${fieldList([
      ["Контакт", item.contact_name],
      ["Посада", item.contact_role],
      ["Email", item.email],
      ["Телефон", item.phone],
      ["KVK", item.kvk],
      ["BTW", item.btw],
      ["Адреса", item.address],
      ["Сайт", item.website],
      ["Регіон", item.region],
      ["Потрібна спеціалізація", item.desired_profession],
      ["Очікувана кількість", item.expected_count],
      ["SNA", item.sna],
    ])}
    <div class="card" style="margin:24px 0"><h3>Коментар компанії</h3><p>${esc(item.description || "—")}</p></div>
    ${snaBlock(item)}
    ${documentsBlock(item.documents)}
    ${statusForm("companies", item)}</div>`;
}

async function requestsPage() {
  const items = await request("/admin/requests");
  const meta = slicePage(items);
  const rows = meta.rows.map(
    (item) => `<tr>
      <td><a href="${adminHref(`requests/${item.id}`)}">${esc(item.public_id)}</a></td>
      <td>${esc(item.project)}</td>
      <td>${esc(item.company_name)}</td>
      <td>${esc(item.profession)}</td>
      <td>${esc(item.start_date || "—")}</td>
      <td><span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></td>
      <td>${rowActions(adminHref(`requests/${item.id}`), "requests", item.id, item.public_id)}</td>
    </tr>`
  );
  return `${pageHead("Заявки", "Concept → Ingediend → In behandeling → Kandidaat geselecteerd → Bevestigd → Afgerond / Geannuleerd")}${table(
    ["Заявка", "Проєкт", "Компанія", "Спеціалізація", "Старт", "Статус", "Дії"],
    rows
  )}${listFoot("requests", meta)}`;
}

async function requestDetail(id) {
  const item = await request(`/admin/requests/${id}`);
  const statuses = [
    ["submitted", "Ingediend"],
    ["in_progress", "In behandeling"],
    ["candidate", "Kandidaat geselecteerd"],
    ["confirmed", "Bevestigd"],
    ["done", "Afgerond"],
    ["cancelled", "Geannuleerd"],
  ];
  return `<div class="admin-record"><a href="${adminHref("requests")}" class="back-link">${icon("arrow-left")} До заявок</a>
    <h1>Заявка ${esc(item.public_id)}</h1>
    <p>${esc(item.company?.company_name || "")} · ${esc(item.status_label)}</p>
    ${fieldList([
      ["Проєкт", item.project],
      ["Адреса об’єкта", item.site_address],
      ["Дата старту", item.start_date],
      ["Тривалість", item.duration],
      ["Графік", item.schedule],
      ["Кількість майстрів", item.workers_count],
      ["Майстер", item.craftsman ? `#${item.craftsman.id} ${item.craftsman.profession}` : "Ще не призначено"],
    ])}
    <div class="card" style="margin:24px 0"><h3>Опис робіт</h3><p>${esc(item.work_description || "—")}</p><h3>Додаткові вимоги</h3><p>${esc(item.requirements || "—")}</p></div>
    <form id="request-status-form" class="card" data-id="${item.id}">
      <label><span>Статус</span><select name="status">${statuses
        .map(([value, label]) => `<option value="${value}" ${item.status === value ? "selected" : ""}>${label}</option>`)
        .join("")}</select></label>
      <button class="btn" style="margin-top:20px">Оновити статус</button>
    </form>
    <p style="margin-top:24px"><a class="btn light" href="${adminHref(`messages/${item.id}`)}">Перейти до повідомлень ↗</a></p></div>`;
}

const HEARD_KEY = "uhr-admin-heard";
let audioCtx = null;
let inboxSource = null;
let inboxBusy = false;
let inboxStale = false;
let inboxChain = Promise.resolve();

function heardMark() {
  const value = Number(localStorage.getItem(HEARD_KEY) || 0);
  return Number.isFinite(value) ? value : 0;
}

function rememberHeard(id) {
  if (id > heardMark()) localStorage.setItem(HEARD_KEY, String(id));
}

function armSound() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  if (!audioCtx) audioCtx = new Ctx();
  if (audioCtx.state === "suspended") audioCtx.resume();
}

function playPing() {
  armSound();
  if (!audioCtx || audioCtx.state !== "running") return;
  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(880, now);
  osc.frequency.setValueAtTime(1175, now + 0.14);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.07, now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start(now);
  osc.stop(now + 0.34);
}

function waitingThreads(threads) {
  return (threads || []).filter((item) => item.last_sender === "company" && item.last_message_id);
}

function setMessageBadge(count) {
  const link = document.querySelector(`.admin-nav a[href="${adminHref("messages")}"]`);
  if (!link) return;
  let badge = link.querySelector(".admin-nav-badge");
  if (!count) {
    badge?.remove();
    return;
  }
  if (!badge) {
    badge = document.createElement("span");
    badge.className = "admin-nav-badge";
    link.append(badge);
  }
  badge.textContent = String(count);
}

function anketaLabel(count) {
  const n = Math.abs(count) % 100;
  const n1 = n % 10;
  if (n > 10 && n < 20) return `${count} анкет`;
  if (n1 === 1) return `${count} анкета`;
  if (n1 > 1 && n1 < 5) return `${count} анкети`;
  return `${count} анкет`;
}

function selectionBlock(people, project) {
  if (people?.length) {
    const cards = people
      .map(
        (person) => `<button type="button" class="admin-pick${String(state.openAnketa) === String(person.id) ? " is-open" : ""}" data-anketa="${person.id}">
          <b>${esc(person.name || "Без імені")}</b>
          <span><small>Професія</small>${esc(person.profession || "—")}</span>
          <span><small>Місто</small>${esc(person.city || "—")}</span>
        </button>`
      )
      .join("");
    return `<section class="admin-selection"><strong>Обрані анкети</strong><div class="admin-pick-list">${cards}</div></section>`;
  }
  if (project === "Selectie") {
    return `<section class="admin-selection"><strong>Обрані анкети</strong><p>У цій розмові ще немає збережених анкет. Вони з’являться тут, щойно компанія надішле свій вибір.</p></section>`;
  }
  return "";
}

async function watchInbox() {
  if (!state.user || inboxBusy) return;
  inboxBusy = true;
  try {
    const data = await request("/admin/messages");
    const waiting = waitingThreads(data.threads);
    setMessageBadge(waiting.length);
    const newest = waiting.reduce((max, item) => Math.max(max, item.last_message_id || 0), 0);
    rememberHeard(newest);
  } catch {
    /* лічильник оновиться з наступним повідомленням */
  } finally {
    inboxBusy = false;
  }
}

function showIncoming(data) {
  if (!data || data.type !== "message" || data.sender_role !== "company") return;
  if (data.message_id && data.message_id <= heardMark()) return;
  if (data.message_id) rememberHeard(data.message_id);
  playPing();
  const field = document.querySelector("#chat-form textarea");
  const draft = Boolean(field?.value.trim());
  const onMessages = route()[0] === "messages";
  if (onMessages && !draft) {
    inboxChain = inboxChain.then(() => render()).catch(() => {});
    return;
  }
  if (draft) inboxStale = true;
  const badge = Number(document.querySelector(".admin-nav-badge")?.textContent || 0);
  setMessageBadge(badge + 1);
  const who = data.company_name ? ` · ${data.company_name}` : "";
  toast(`Нове повідомлення${who}.`);
}

function startInboxWatch() {
  if (inboxSource || !state.user) return;
  document.addEventListener("pointerdown", armSound, { once: true });
  document.addEventListener("focusout", (event) => {
    if (!inboxStale || event.target?.name !== "message" || event.target.value.trim()) return;
    inboxStale = false;
    render();
  });
  watchInbox();
  const source = new EventSource("/api/v1/admin/messages/stream");
  inboxSource = source;
  source.onmessage = (event) => {
    try {
      showIncoming(JSON.parse(event.data));
    } catch {
      /* службовий кадр потоку */
    }
  };
}

async function messagesPage(id) {
  const data = await request("/admin/messages" + (id ? `?request_id=${id}` : ""));
  setMessageBadge(waitingThreads(data.threads).length);
  const threads =
    data.threads
      .map((item) => {
        const active = String(data.current?.id) === String(item.id);
        const fresh = item.last_sender === "company" && item.last_message_id;
        const picks = (item.selection || []).length;
        return `<a class="admin-thread${active ? " is-active" : ""}${fresh ? " is-new" : ""}" href="${adminHref(`messages/${item.id}`)}">
          <strong>${esc(item.public_id)} · ${esc(item.project || "Без назви")}${fresh ? `<b class="admin-new">Нове</b>` : ""}</strong>
          <span>${esc(item.company_name || "Компанію не вказано")}</span>
          <p>${esc(item.last_message || "Немає повідомлень")}</p>
          ${picks ? `<span class="admin-pick-count">${anketaLabel(picks)}</span>` : ""}
          <em>${fmtTime(item.updated_at)}</em>
        </a>`;
      })
      .join("") || `<div class="admin-thread-empty">Немає діалогів. Вони з’являться після заявок компаній.</div>`;
  const opened = data.current;
  const company = opened ? data.threads.find((item) => String(item.id) === String(opened.id)) : null;
  const people = opened?.selection?.length ? opened.selection : company?.selection || [];
  const chat = opened
    ? `<header class="admin-thread-head">
        <div><strong>${esc(opened.public_id)} · ${esc(opened.project || "Без назви")}</strong><span>${esc(company?.company_name || "")}</span></div>
        <a href="${adminHref(`requests/${opened.id}`)}">Заявка</a>
      </header>
      ${selectionBlock(people, opened.project || company?.project)}
      <div class="admin-bubbles">
        ${
          opened.messages
            .map(
              (msg) => `<article class="admin-bubble${msg.sender_role === "admin" ? " is-mine" : ""}">
                <p>${esc(msg.body)}</p><time>${fmtTime(msg.created_at)}</time>
              </article>`
            )
            .join("") || `<div class="admin-thread-empty">Повідомлень ще немає.</div>`
        }
      </div>
      <form id="chat-form" class="admin-composer" data-id="${opened.id}">
        <textarea name="message" aria-label="Повідомлення" placeholder="Написати повідомлення…" required></textarea>
        <button class="btn">Надіслати</button>
      </form>`
    : `<div class="admin-thread-empty"><p>Оберіть заявку зі списку зліва.</p></div>`;
  return `${pageHead("Повідомлення", "Листування з компаніями по заявках.")}
    <div class="admin-fill"><div class="admin-inbox${state.openAnketa ? " has-anketa" : ""}"><aside class="admin-threads">${threads}</aside><section class="admin-conversation">${chat}</section><aside class="admin-anketa"></aside></div></div>`;
}

function filledValue(value) {
  if (value === null || value === undefined || value === false) return false;
  return String(value).trim() !== "";
}

function anketaText(item) {
  const rows = [
    ["Ім’я", item.name],
    ["Професія", item.profession],
    ["Місто", item.city],
    ["Телефон", item.phone],
    ["Email", item.email],
    ["Перелік робіт", item.works],
    ["Досвід роботи в Україні", item.experience_ua],
    ["Досвід роботи в Нідерландах", item.experience_nl],
    ["Мова", item.language],
    ["Компанія", item.company_name],
    ["KVK", item.kvk],
    ["BTW", item.btw],
    ["Адреса", item.address],
    ["Сайт", item.website],
    ["Instagram", item.instagram],
    ["Facebook", item.facebook],
    ["TikTok", item.tiktok],
    ["Додаткові роботи", item.extra_work],
    ["Досвід, років", item.experience_years],
    ["Ставка €/год", item.hourly_rate],
    ["Радіус, км", item.radius_km],
    ["Доступність", item.availability],
    ["По всій країні", item.nationwide ? "Так" : ""],
    ["Портфоліо", item.portfolio_url],
    ["Опис досвіду", item.description],
  ].filter(([, value]) => filledValue(value));
  const files = (item.documents || []).map((doc) => doc.original_name).filter(Boolean);
  if (files.length) rows.push(["Файли", files.join(", ")]);
  return rows
    .map(([label, value]) => `<p><small>${esc(label)}</small>${esc(value)}</p>`)
    .join("");
}

function closeAnketa() {
  state.openAnketa = "";
  document.querySelector(".admin-inbox")?.classList.remove("has-anketa");
  document.querySelectorAll("[data-anketa]").forEach((button) => button.classList.remove("is-open"));
  const pane = document.querySelector(".admin-anketa");
  if (pane) pane.innerHTML = "";
}

async function openAnketa(id) {
  state.openAnketa = String(id);
  document.querySelectorAll("[data-anketa]").forEach((button) => {
    button.classList.toggle("is-open", button.dataset.anketa === String(id));
  });
  const inbox = document.querySelector(".admin-inbox");
  const pane = document.querySelector(".admin-anketa");
  if (!inbox || !pane) return;
  inbox.classList.add("has-anketa");
  pane.innerHTML = `<p>Завантаження…</p>`;
  try {
    const item = await request(`/admin/craftsmen/${id}`);
    pane.innerHTML = `<header><strong>${esc(item.name || "Без імені")}</strong><button type="button" data-anketa-close>Закрити</button></header><div class="admin-anketa-body">${anketaText(item) || "<p>Заповнених полів немає.</p>"}</div>`;
  } catch (error) {
    pane.innerHTML = `<header><strong>Анкета</strong><button type="button" data-anketa-close>Закрити</button></header><p>${esc(error.message)}</p>`;
  }
}

async function render() {
  const [page, arg, arg2] = route();
  if (!state.user) {
    app.innerHTML = loginPage();
    icons();
    return;
  }
  try {
    let content = "";
    let active = page;
    if (page === "masters" && arg) content = await masterDetail(arg);
    else if (page === "masters") content = await masters();
    else if (page === "companies" && arg) content = await companyDetail(arg);
    else if (page === "companies") content = await companies();
    else if (page === "requests" && arg) content = await requestDetail(arg);
    else if (page === "requests") content = await requestsPage();
    else if (page === "messages") content = await messagesPage(arg);
    else if (page === "settings") content = await siteSettings();
    else if (page === "cms") content = await renderCms(arg, arg2, route()[3]);
    else {
      content = await overview();
      active = "overview";
    }
    paint(content, active);
  } catch (error) {
    if (error.status === 401) {
      state.user = null;
      app.innerHTML = loginPage("Сесію закінчено. Увійдіть знову.");
    } else {
      paint(`<div class="card empty"><h1>Помилка</h1><p>${esc(error.message)}</p></div>`, page);
    }
  }
  icons();
  document.querySelector(".admin-bubbles")?.scrollTo(0, 99999);
  if (page === "messages" && state.openAnketa) await openAnketa(state.openAnketa);
  if (page === "cms") await mountCms(arg);
  if (state.user) startInboxWatch();
}

app.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    if (await handleCmsSubmit(form)) {
      toast("Зміни збережено.");
      if (!["cms-new-page-form"].includes(form.id)) await render();
      return;
    }
    if (form.id === "login-form") {
      const data = new FormData(form);
      state.user = await request("/auth/login", {
        method: "POST",
        json: { email: data.get("email"), password: data.get("password") },
      });
      navigate("overview");
      return;
    }
    if (form.id === "status-form") {
      const status = event.submitter?.dataset.status;
      const data = new FormData(form);
      await request(`/admin/${form.dataset.prefix}/${form.dataset.id}/status`, {
        method: "POST",
        json: { status, comment: data.get("comment") || "" },
      });
      toast("Статус оновлено.");
      await render();
      return;
    }
    if (form.id === "request-status-form") {
      const data = new FormData(form);
      await request(`/admin/requests/${form.dataset.id}/status`, {
        method: "POST",
        json: { status: data.get("status") },
      });
      toast("Статус заявки оновлено.");
      await render();
      return;
    }
    if (form.id === "chat-form") {
      const data = new FormData(form);
      await request("/admin/messages", {
        method: "POST",
        json: { request_id: Number(form.dataset.id), body: data.get("message") },
      });
      await render();
      return;
    }
    if (form.classList.contains("site-settings-form")) {
      const isOpen = form.elements.is_open.checked;
      await request(`/admin/sites/${form.dataset.site}`, {
        method: "PUT",
        json: { is_open: isOpen },
      });
      toast(isOpen ? "Сайт відкрито для всіх." : "Сайт закрито сторінкою очікування.");
      await render();
      return;
    }
  } catch (error) {
    toast(error.message);
  }
});

app.addEventListener("click", async (event) => {
  const anketa = event.target.closest("[data-anketa]");
  if (anketa) {
    event.preventDefault();
    await openAnketa(anketa.dataset.anketa);
    return;
  }
  if (event.target.closest("[data-anketa-close]")) {
    closeAnketa();
    return;
  }
  const link = event.target.closest("a[href]");
  if (
    link &&
    !link.hasAttribute("data-logout") &&
    link.target !== "_blank" &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey
  ) {
    const url = new URL(link.href, location.origin);
    if (url.origin === location.origin && (url.pathname === "/admin" || url.pathname.startsWith("/admin/"))) {
      event.preventDefault();
      const path = url.pathname === "/admin" || url.pathname === "/admin/" ? "" : url.pathname.slice("/admin/".length);
      navigate(`${path}${url.search}`);
      return;
    }
  }
  try {
    if (await handleCmsClick(event.target)) return;
  } catch (error) {
    toast(error.message);
    return;
  }
  const preview = event.target.closest("[data-preview-site]");
  if (preview) {
    const popup = window.open("about:blank", "_blank");
    if (popup) popup.opener = null;
    try {
      const data = await request(`/admin/sites/${preview.dataset.previewSite}/preview-link`);
      if (popup) popup.location.href = data.url;
      else window.location.href = data.url;
    } catch (error) {
      popup?.close();
      toast(error.message);
    }
    return;
  }
  const remove = event.target.closest("[data-delete]");
  if (remove) {
    event.preventDefault();
    const kind = { craftsmen: "анкету", companies: "компанію", requests: "заявку" }[remove.dataset.delete] || "запис";
    const extra = remove.dataset.delete === "companies" ? " Заявки цієї компанії теж буде видалено." : "";
    if (!confirm(`Видалити ${kind} «${remove.dataset.label}»?${extra} Цю дію не можна скасувати.`)) return;
    try {
      await request(`/admin/${remove.dataset.delete}/${remove.dataset.id}`, { method: "DELETE" });
      toast("Запис видалено.");
      const [section, detail] = route();
      const list = section === "masters" || section === "companies" || section === "requests" ? section : "overview";
      if (detail) navigate(list);
      else await render();
    } catch (error) {
      toast(error.message);
    }
    return;
  }
  const logout = event.target.closest("[data-logout]");
  if (!logout) return;
  event.preventDefault();
  await request("/auth/logout", { method: "POST", json: {} });
  window.location.href = "/";
});

app.addEventListener("change", (event) => {
  if (handleCmsChange(event.target)) return;
  if (event.target.id === "status-filter") {
    const value = event.target.value;
    const section = event.target.dataset.section || "masters";
    navigate(value ? `${section}?status=${encodeURIComponent(value)}` : section);
    return;
  }
});

window.addEventListener("popstate", render);
window.addEventListener("cms-toast", (event) => toast(event.detail));

adoptLegacyHash();

try {
  state.user = await request("/auth/me");
} catch {
  state.user = null;
}
await render();
