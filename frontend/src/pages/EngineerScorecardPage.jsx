import { useState } from "react";
import { Bar, Pie } from "react-chartjs-2";
import DateRangeFilter from "../components/DateRangeFilter";
import ErrorState from "../components/ErrorState";
import KpiCard from "../components/KpiCard";
import LoadingState from "../components/LoadingState";
import PanelTitle from "../components/PanelTitle";
import { getEngineerDashboard } from "../lib/api";

function parseError(err) {
  return err?.response?.data?.error || err?.response?.data?.detail || err?.message || "Request failed";
}

export default function EngineerScorecardPage() {
  const [engineerName, setEngineerName] = useState("");
  const [submittedName, setSubmittedName] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [range, setRange] = useState({ startDate: "", endDate: "" });

  async function onSubmit(e) {
    e.preventDefault();
    const clean = engineerName.trim();
    if (!clean) return;
    try {
      setLoading(true);
      setError("");
      const res = await getEngineerDashboard(clean);
      setData(res.data);
      setSubmittedName(clean);
    } catch (err) {
      setError(parseError(err));
    } finally {
      setLoading(false);
    }
  }

  const pieData = data
    ? {
        labels: ["SLA Met", "Reopened"],
        datasets: [
          {
            data: [data.sla_pct, data.reopen_pct],
            backgroundColor: ["#06b6d4", "#f59e0b"],
          },
        ],
      }
    : null;

  const barData = data
    ? {
        labels: ["Tickets", "SLA %", "Reopen %", "Productivity"],
        datasets: [
          {
            label: "Engineer Score",
            data: [data.tickets_handled, data.sla_pct, data.reopen_pct, data.productivity_score],
            backgroundColor: ["#334155", "#0ea5e9", "#f97316", "#10b981"],
          },
        ],
      }
    : null;

  return (
    <div className="space-y-4">
      <div className="panel p-5 animate-rise">
        <PanelTitle
          title="Engineer Scorecard"
          subtitle="Engineer-level workload, SLA performance, and productivity scoring."
        />
        <form onSubmit={onSubmit} className="mt-3 flex flex-col gap-2 md:flex-row">
          <input
            value={engineerName}
            onChange={(e) => setEngineerName(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
            placeholder="Enter engineer name (example: John Doe)"
          />
          <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900">
            Load Scorecard
          </button>
        </form>
      </div>

      <DateRangeFilter value={range} onChange={setRange} />

      {loading ? <LoadingState message="Loading engineer metrics..." /> : null}
      {error ? <ErrorState message={error} /> : null}

      {data ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <KpiCard label="Engineer" value={submittedName} />
            <KpiCard label="Tickets Handled" value={data.tickets_handled} />
            <KpiCard label="SLA %" value={`${data.sla_pct}%`} tone="good" />
            <KpiCard label="Productivity" value={data.productivity_score} tone="warn" />
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="panel p-4 animate-rise">
              <PanelTitle title="SLA vs Reopen Mix" />
              <Pie data={pieData} />
            </div>
            <div className="panel p-4 animate-rise">
              <PanelTitle title="Performance Profile" />
              <Bar data={barData} />
            </div>
          </div>
        </>
      ) : (
        <div className="panel p-8 text-center text-slate-600">
          Enter an engineer name to load the scorecard.
        </div>
      )}
    </div>
  );
}
