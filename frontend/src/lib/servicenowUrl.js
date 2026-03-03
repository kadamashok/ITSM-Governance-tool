export function normalizeServiceNowUrl(rawUrl) {
  const input = (rawUrl || "").trim();
  if (!input) {
    return { ok: false, error: "Invalid URL. Please enter base instance URL (e.g., https://instance.company.com)" };
  }

  const baseHttpsRegex = /^https:\/\/[A-Za-z0-9.-]+(?::\d{1,5})?\/?$/;
  if (!baseHttpsRegex.test(input)) {
    return {
      ok: false,
      error: "Invalid URL. Please enter base instance URL (e.g., https://instance.company.com)",
    };
  }

  let parsed;
  try {
    parsed = new URL(input);
  } catch {
    return {
      ok: false,
      error: "Invalid URL. Please enter base instance URL (e.g., https://instance.company.com)",
    };
  }

  const normalizedUrl = parsed.origin;
  return { ok: true, normalizedUrl };
}
