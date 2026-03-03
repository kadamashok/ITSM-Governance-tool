import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/executive", label: "Executive Dashboard" },
  { to: "/vendor", label: "Vendor Scorecard" },
  { to: "/engineer", label: "Engineer Scorecard" },
  { to: "/governance", label: "Governance View" },
  { to: "/settings/servicenow", label: "ServiceNow Settings", alwaysEnabled: true },
];

export default function AppShell({ children, dashboardEnabled }) {
  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-[1400px] px-3 py-4 md:px-6 md:py-8">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[290px_1fr]">
          <aside className="panel p-5 animate-rise md:sticky md:top-6 md:h-[calc(100vh-3rem)]">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-brand-600 font-semibold">ITSM Governance</p>
              <h1 className="mt-2 font-sans text-2xl font-extrabold text-ink-950">
                Command Center
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Enterprise monitoring for SLA, operations quality, and delivery productivity.
              </p>
            </div>
            <nav className="mt-6 space-y-2">
              {navItems.map((item) => (
                item.alwaysEnabled || dashboardEnabled ? (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `block rounded-xl px-3 py-2 text-sm font-semibold transition ${
                        isActive
                          ? "bg-brand-600 text-white shadow-lg shadow-brand-600/30"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ) : (
                  <span
                    key={item.to}
                    className="block cursor-not-allowed rounded-xl bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-400"
                  >
                    {item.label}
                  </span>
                )
              ))}
            </nav>
            {!dashboardEnabled ? (
              <p className="mt-4 text-xs text-slate-500">
                Configure and connect ServiceNow to unlock dashboard pages.
              </p>
            ) : null}
          </aside>
          <main className="space-y-4">{children}</main>
        </div>
      </div>
    </div>
  );
}
