import { request } from "./api.js";

const app = document.querySelector("#app");
const state = { user: null, toast: "" };

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
const route = () => ((location.hash.slice(1) || "overview").split("?")[0] || "overview").split("/");
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("uk-UA") : "—");
const badgeClass = (status) => (status === "approved" || status === "confirmed" || status === "done" ? "" : "yellow");

const NAV = [
  ["overview", "layout-dashboard", "Огляд"],
  ["masters", "users", "Анкети майстрів"],
  ["companies", "building-2", "Компанії"],
  ["requests", "clipboard-list", "Заявки"],
  ["texts", "languages", "Тексти сайтів"],
  ["settings", "settings", "Налаштування"],
];
const EXTRA = [["messages", "messages-square", "Повідомлення"]];

function brand() {
  return `<a href="#overview" class="brand">UHR · Admin</a>`;
}

function shell(content, page) {
  const link = ([id, name, label]) =>
    `<a class="${page === id ? "active" : ""}" ${page === id ? 'aria-current="page"' : ""} href="#${id}">${icon(name)}${label}</a>`;
  return `<div class="workspace">
    <header class="workspace-header"><div class="workspace-nav">${brand()}
      <nav aria-label="Адмінка">${NAV.map(link).join("")}</nav>
      <details class="account-menu">
        <summary>${icon("building-2")}<span>${esc(state.user?.name || "Менеджер")}</span>${icon("chevron-down")}</summary>
        <div class="dropdown">${EXTRA.map(link).join("")}<a href="#logout" data-logout>${icon("log-out")}Вийти</a></div>
      </details>
    </div></header>
    <main class="content">
      <div class="topbar"><span>Спільна адмінка · Ukrwerkspot + UHR</span><span>${esc(state.user?.email || "")}</span></div>
      ${content}
    </main>
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
    <h1>Спільна адмінка</h1>
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

function statusFilter(current, extra = []) {
  const options = [["", "Усі статуси"], ["pending", "На перевірці"], ["clarification", "Уточнення"], ["approved", "Схвалено"], ["rejected", "Відхилено"], ...extra];
  return `<select id="status-filter" style="max-width:260px;margin-bottom:20px">${options
    .map(([value, label]) => `<option value="${value}" ${current === value ? "selected" : ""}>${label}</option>`)
    .join("")}</select>`;
}

async function overview() {
  const data = await request("/admin/overview");
  const cards = [
    ["Нові анкети", data.new_masters, "#masters", "Перевірка VCA та професійного досвіду."],
    ["Компанії на перевірці", data.companies_review, "#companies", "Перевірка юридичних даних та документів."],
    ["Активні заявки", data.active_requests, "#requests", "Планування та узгодження з компаніями."],
    ["Опубліковані профілі", data.published_profiles, "#masters", "Обезличені профілі для каталогу UHR."],
  ];
  return shell(`
    <div class="eyebrow">Єдина екосистема · два домени</div>
    <h1>Центр управління UHR</h1>
    <p>Ukrwerkspot збирає анкети майстрів. UHR приймає компанії. Тексти Ukrwerkspot редагуються тут.</p>
    <div class="stats">${cards
      .map(([label, value]) => `<div class="card">${esc(label)}<strong>${esc(value)}</strong>Overzicht</div>`)
      .join("")}</div>
    <div class="grid">${cards
      .map(
        ([label, , href, text]) =>
          `<a class="card" href="${href}"><h3>${esc(label)} ↗</h3><p>${esc(text)}</p></a>`
      )
      .join("")}</div>`, "overview");
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
  return shell(
    `<h1>Відкрити або закрити сайти</h1>
    <p>У закритому режимі звичайний відвідувач бачить заглушку. Кнопка перегляду відкриває повний сайт тільки для адміністратора.</p>
    <div class="grid">${cards}</div>
    <div class="note">Доступ до закритого Ukrwerkspot передається окремою захищеною cookie на 1 годину, тому що браузер не дозволяє спільну cookie для двох різних доменів.</div>`,
    "settings"
  );
}

function table(headers, rows) {
  if (!rows.length) return `<div class="card empty">Поки що немає записів.</div>`;
  return `<div class="card table-scroll"><table>
    <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.join("")}</tbody>
  </table></div>`;
}

async function masters() {
  const status = new URLSearchParams(location.hash.split("?")[1] || "").get("status") || "";
  const items = await request("/admin/craftsmen" + (status ? `?status=${encodeURIComponent(status)}` : ""));
  const rows = items.map(
    (item) => `<tr>
      <td><a href="#masters/${item.id}">#${item.id} ↗</a></td>
      <td>${esc(item.name)}</td>
      <td>${esc(item.profession)}</td>
      <td>${esc(item.city)}</td>
      <td>${esc(item.source)}</td>
      <td><span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></td>
      <td>${fmtDate(item.created_at)}</td>
    </tr>`
  );
  return shell(
    `<h1>Перевірка майстрів</h1><p>Анкети з Ukrwerkspot. Після схвалення публікується лише професійний профіль без імені та контактів.</p>${statusFilter(status)}${table(
      ["ID", "Ім’я", "Спеціалізація", "Місто", "Джерело", "Статус", "Дата"],
      rows
    )}`,
    "masters"
  );
}

function fieldList(pairs) {
  return `<div class="fields">${pairs
    .map(
      ([label, value]) =>
        `<label class="${String(value).length > 80 ? "full" : ""}"><span>${esc(label)}</span><div class="note" style="margin:0">${esc(value || "—")}</div></label>`
    )
    .join("")}</div>`;
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
  return shell(
    `<a href="#masters" class="back-link">${icon("arrow-left")} До анкет</a>
    <div class="eyebrow">Ukrwerkspot · анкета #${item.id}</div>
    <h1>${esc(item.name || "Без імені")}</h1>
    <p>${esc(item.profession)} · ${esc(item.city)} · ${esc(item.status_label)}</p>
    ${fieldList([
      ["Телефон", item.phone],
      ["Email", item.email],
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
    ${statusForm("craftsmen", item)}`,
    "masters"
  );
}

async function companies() {
  const items = await request("/admin/companies");
  const rows = items.map(
    (item) => `<tr>
      <td><a href="#companies/${item.id}">#${item.id} ↗</a></td>
      <td>${esc(item.company_name)}</td>
      <td>${esc(item.contact_name)}</td>
      <td>${esc(item.source)}</td>
      <td><span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></td>
      <td>${fmtDate(item.created_at)}</td>
    </tr>`
  );
  return shell(
    `<h1>Перевірка компаній</h1><p>Реєстрації з uhrbv.nl. Після перевірки компанія отримає доступ до каталогу.</p>${table(
      ["ID", "Компанія", "Контакт", "Джерело", "Статус", "Дата"],
      rows
    )}`,
    "companies"
  );
}

async function companyDetail(id) {
  const item = await request(`/admin/companies/${id}`);
  return shell(
    `<a href="#companies" class="back-link">${icon("arrow-left")} До компаній</a>
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
    <div class="card" style="margin:24px 0"><h3>Опис компанії</h3><p>${esc(item.description || "—")}</p></div>
    ${statusForm("companies", item)}`,
    "companies"
  );
}

async function requestsPage() {
  const items = await request("/admin/requests");
  const rows = items.map(
    (item) => `<tr>
      <td><a href="#requests/${item.id}">${esc(item.public_id)} ↗</a></td>
      <td>${esc(item.project)}</td>
      <td>${esc(item.company_name)}</td>
      <td>${esc(item.profession)}</td>
      <td>${esc(item.start_date || "—")}</td>
      <td><span class="badge ${badgeClass(item.status)}">${esc(item.status_label)}</span></td>
    </tr>`
  );
  return shell(
    `<h1>Заявки компаній</h1><p>Concept → Ingediend → In behandeling → Kandidaat geselecteerd → Bevestigd → Afgerond / Geannuleerd</p>${table(
      ["Заявка", "Проєкт", "Компанія", "Спеціалізація", "Старт", "Статус"],
      rows
    )}`,
    "requests"
  );
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
  return shell(
    `<a href="#requests" class="back-link">${icon("arrow-left")} До заявок</a>
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
    <p style="margin-top:24px"><a class="btn light" href="#messages/${item.id}">Перейти до повідомлень ↗</a></p>`,
    "requests"
  );
}

async function messagesPage(id) {
  const data = await request("/admin/messages" + (id ? `?request_id=${id}` : ""));
  const threads = data.threads
    .map(
      (item) => `<a class="card" href="#messages/${item.id}" style="display:block;margin-bottom:12px">
        <h3>${esc(item.public_id)} · ${esc(item.project || "Без назви")}</h3>
        <p>${esc(item.company_name)}</p>
        <span class="muted">${esc(item.last_message || "Немає повідомлень")}</span>
      </a>`
    )
    .join("") || `<div class="card empty">Немає діалогів. Вони з’являться після заявок компаній.</div>`;
  const chat = data.current
    ? `<div class="card">
        <h3>${esc(data.current.public_id)} · ${esc(data.current.project)}</h3>
        ${
          data.current.messages
            .map(
              (msg) =>
                `<div class="bubble ${msg.sender_role === "admin" ? "mine" : ""}">${esc(msg.body)}<div class="muted">${fmtDate(msg.created_at)}</div></div>`
            )
            .join("") || `<div class="note">Повідомлень ще немає.</div>`
        }
        <form id="chat-form" class="actions" data-id="${data.current.id}">
          <input name="message" aria-label="Повідомлення" placeholder="Написати повідомлення…" required style="flex:1">
          <button class="btn">Надіслати →</button>
        </form>
      </div>`
    : `<div class="card empty">Оберіть заявку зліва.</div>`;
  return shell(`<h1>Повідомлення менеджера</h1><p>Уся комунікація з компаніями йде через UHR.</p><div class="chat"><aside>${threads}</aside>${chat}</div>`, "messages");
}

async function textsPage(site = "ukrwerkspot", page = "coming_soon") {
  const meta = await request("/admin/texts/meta");
  const items = await request(`/admin/texts?site=${encodeURIComponent(site)}&page=${encodeURIComponent(page)}`);
  const siteOptions = meta.sites
    .map((item) => `<option value="${item.id}" ${item.id === site ? "selected" : ""}>${esc(item.label)}</option>`)
    .join("");
  const pageOptions = (meta.pages[site] || [])
    .map((item) => `<option value="${item.id}" ${item.id === page ? "selected" : ""}>${esc(item.label)}</option>`)
    .join("");
  const fields = items
    .map(
      (item) => `<label class="full">
        <span>${esc(item.label)} <span class="muted">${esc(item.key)}</span></span>
        <textarea name="${item.id}" rows="${item.value.length > 80 ? 4 : 2}">${esc(item.value)}</textarea>
      </label>`
    )
    .join("");
  return shell(
    `<h1>Тексти сайтів</h1>
    <p>Заглушки ukrwerkspot.nl і uhrbv.nl беруть тексти звідси. Після збереження оновіть відкриту вкладку сайту.</p>
    <form id="texts-nav" class="fields" style="margin-bottom:24px">
      <label><span>Сайт</span><select name="site">${siteOptions}</select></label>
      <label><span>Сторінка</span><select name="page">${pageOptions}</select></label>
    </form>
    <form id="texts-form" class="card">
      <div class="fields">${fields || "<p>Для цієї сторінки ключів ще немає.</p>"}</div>
      <button class="btn" style="margin-top:25px">Зберегти тексти</button>
    </form>`,
    "texts"
  );
}

async function render() {
  const [page, arg, arg2] = route();
  if (!state.user) {
    app.innerHTML = loginPage();
    icons();
    return;
  }
  try {
    if (page === "masters" && arg) app.innerHTML = await masterDetail(arg);
    else if (page === "masters") app.innerHTML = await masters();
    else if (page === "companies" && arg) app.innerHTML = await companyDetail(arg);
    else if (page === "companies") app.innerHTML = await companies();
    else if (page === "requests" && arg) app.innerHTML = await requestDetail(arg);
    else if (page === "requests") app.innerHTML = await requestsPage();
    else if (page === "messages") app.innerHTML = await messagesPage(arg);
    else if (page === "texts") {
      const site = arg || "ukrwerkspot";
      const defaultPage = "coming_soon";
      app.innerHTML = await textsPage(site, arg2 || defaultPage);
    }
    else if (page === "settings") app.innerHTML = await siteSettings();
    else app.innerHTML = await overview();
  } catch (error) {
    if (error.status === 401) {
      state.user = null;
      app.innerHTML = loginPage("Сесію закінчено. Увійдіть знову.");
    } else {
      app.innerHTML = shell(`<div class="card empty"><h1>Помилка</h1><p>${esc(error.message)}</p></div>`, page);
    }
  }
  icons();
  window.scrollTo(0, 0);
}

app.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    if (form.id === "login-form") {
      const data = new FormData(form);
      state.user = await request("/auth/login", {
        method: "POST",
        json: { email: data.get("email"), password: data.get("password") },
      });
      location.hash = "overview";
      await render();
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
    if (form.id === "texts-form") {
      const items = [...form.querySelectorAll("textarea[name]")].map((el) => ({
        id: Number(el.name),
        value: el.value,
      }));
      await request("/admin/texts", { method: "PUT", json: { items } });
      toast("Тексти збережено. Ukrwerkspot покаже нову версію.");
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
  const logout = event.target.closest("[data-logout]");
  if (!logout) return;
  event.preventDefault();
  await request("/auth/logout", { method: "POST", json: {} });
  window.location.href = "/";
});

app.addEventListener("change", (event) => {
  if (event.target.id === "status-filter") {
    const value = event.target.value;
    location.hash = value ? `masters?status=${value}` : "masters";
    return;
  }
  const nav = event.target.closest("#texts-nav");
  if (nav) {
    const data = new FormData(nav);
    const site = data.get("site");
    const pageName = event.target.name === "site" ? "coming_soon" : data.get("page");
    location.hash = `texts/${site}/${pageName}`;
  }
});

window.addEventListener("hashchange", render);

try {
  state.user = await request("/auth/me");
} catch {
  state.user = null;
}
await render();
