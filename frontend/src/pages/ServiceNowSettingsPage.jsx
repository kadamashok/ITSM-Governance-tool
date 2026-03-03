import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PanelTitle from "../components/PanelTitle";
import { getServiceNowStatus, saveServiceNowOAuthConfig } from "../lib/api";
import { normalizeServiceNowUrl } from "../lib/servicenowUrl";

function parseError(err) {
  if (!err?.response) {
    return "Backend service not running.";
  }
  return (
    err?.response?.data?.error ||
    err?.response?.data?.detail?.error ||
    err?.response?.data?.detail ||
    err?.message ||
    "Request failed"
  );
}

export default function ServiceNowSettingsPage({ onConnected }) {
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({
    instance_url: "",
    client_id: "",
    client_secret: "",
    tenant_id: "",
    oauth_scope: "openid profile offline_access",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState({ type: "", message: "" });
  const [urlError, setUrlError] = useState("");

  useEffect(() => {
    const oauthState = searchParams.get("oauth");
    if (oauthState === "error") {
      setResult({ type: "error", message: "Microsoft OAuth login failed. Please try again." });
    }
    if (oauthState === "success") {
      getServiceNowStatus()
        .then((status) => {
          if (status?.connected) {
            setResult({ type: "success", message: "Connected via Microsoft login." });
            onConnected?.();
          }
        })
        .catch(() => {
          setResult({ type: "error", message: "Backend service not running." });
        });
    }
  }, [onConnected, searchParams]);

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (key === "instance_url") {
      const parsed = normalizeServiceNowUrl(value);
      if (!value.trim()) {
        setUrlError("");
      } else if (!parsed.ok) {
        setUrlError(parsed.error);
      } else {
        setUrlError("");
      }
    }
  }

  function validateAndNormalizeUrl() {
    const parsed = normalizeServiceNowUrl(form.instance_url);
    if (!parsed.ok) {
      setUrlError(parsed.error);
      return null;
    }
    setUrlError("");
    if (parsed.normalizedUrl !== form.instance_url) {
      setForm((prev) => ({ ...prev, instance_url: parsed.normalizedUrl }));
    }
    return parsed.normalizedUrl;
  }

  async function handleMicrosoftLogin() {
    const instanceUrl = validateAndNormalizeUrl();
    if (!instanceUrl) {
      return;
    }

    try {
      setLoading(true);
      setResult({ type: "", message: "" });
      const payload = { ...form, instance_url: instanceUrl };
      await saveServiceNowOAuthConfig(payload);
      window.location.href = "http://127.0.0.1:8050/auth/login";
    } catch (err) {
      setResult({ type: "error", message: parseError(err) });
      setLoading(false);
    }
  }

  return (
    <div className="panel p-6 animate-rise">
      <PanelTitle
        title="ServiceNow OAuth Configuration"
        subtitle="Connect using Azure AD integrated Microsoft login (OAuth 2.0)."
      />

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="text-sm font-semibold text-slate-700">
          ServiceNow Instance URL
          <input
            type="url"
            required
            value={form.instance_url}
            onChange={(e) => updateField("instance_url", e.target.value)}
            onBlur={validateAndNormalizeUrl}
            placeholder="https://company.service-now.com"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
          />
          {urlError ? <p className="mt-1 text-xs text-rose-700">{urlError}</p> : null}
        </label>

        <label className="text-sm font-semibold text-slate-700">
          Tenant ID
          <input
            type="text"
            required
            value={form.tenant_id}
            onChange={(e) => updateField("tenant_id", e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
          />
        </label>

        <label className="text-sm font-semibold text-slate-700">
          Client ID
          <input
            type="text"
            required
            value={form.client_id}
            onChange={(e) => updateField("client_id", e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
          />
        </label>

        <label className="text-sm font-semibold text-slate-700">
          Client Secret
          <input
            type="password"
            required
            value={form.client_secret}
            onChange={(e) => updateField("client_secret", e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
          />
        </label>

        <label className="text-sm font-semibold text-slate-700 md:col-span-2">
          OAuth Scope
          <input
            type="text"
            required
            value={form.oauth_scope}
            onChange={(e) => updateField("oauth_scope", e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
          />
        </label>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleMicrosoftLogin}
          disabled={loading}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Redirecting..." : "Connect via Microsoft Login"}
        </button>
      </div>

      {result.message ? (
        <p className={`mt-4 text-sm ${result.type === "success" ? "text-emerald-700" : "text-rose-700"}`}>
          {result.message}
        </p>
      ) : null}
    </div>
  );
}
