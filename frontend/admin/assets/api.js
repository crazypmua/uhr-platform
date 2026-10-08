export const API = "/api/v1";

function detail(data) {
  if (!data) return "Помилка запиту";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg || item).join("; ");
  return "Помилка запиту";
}

export async function request(path, { method = "GET", json } = {}) {
  const options = { method, credentials: "include", headers: {} };
  if (json !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(json);
  }
  const response = await fetch(API + path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(detail(data));
    error.status = response.status;
    throw error;
  }
  return data;
}
