import { useEffect, useMemo, useState } from "react";
import { Bar, Pie } from "react-chartjs-2";
import DateRangeFilter from "../components/DateRangeFilter";
import ErrorState from "../components/ErrorState";
import KpiCard from "../components/KpiCard";
import LoadingState from "../components/LoadingState";
import PanelTitle from "../components/PanelTitle";
import RankingTable from "../components/RankingTable";
import { getExecutiveDashboard, getVendorDashboard } from "../lib/api";

const defaultVendor = "UNKNOWN_VENDOR";

function parseError(err) {
  return err?.response?.data?.error || err?.response?.data?.detail || err?.message || "Request failed";
}

export default function VendorScorecardPage() {
  const [vendorName, setVendorName] = useState(defaultVendor);
  const [summary, setSummary] = useState(null);
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [range, setRange] = useState({ startDate: "", endDate: "" });

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        const exec = await getExecutiveDashboard();
        setRanking(exec?.data?.vendor_ranking || []);
        const candidate = exec?.data?.vendor_ranking?.[0]?.vendor || defaultVendor;
        setVendorName(candidate);
        const vendor = await getVendorDashboard(candidate);
        setSummary(vendor.data);
      } catch (err) {
        setError(parseError(err));
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  async function applyVendor(vendor) {
    try {
      setLoading(true);
      setError("");
      const res = await getVendorDashboard(vendor);
      setSummary(res.data);
      setVendorName(vendor);
    } catch (err) {
      setError(parseError(err));
    } finally {
      setLoading(false);
    }
  }

  const selectedRow = useMemo(
    () => ranking.find((r) => r.vendor.toLowerCase() === vendorName.toLowerCase()),
    [ranking, vendorName]
  );

  if (loading && !summary) return <LoadingState />;
  if (error && !summary) return <ErrorState message={error} />;

  const pieData = {
    labels: ["SLA Met", "Breached"],
    datasets: [
      {
        data: [summary.sla_pct, Math.max(0, 100 - summary.sla_pct)],
        backgroundColor: ["#10b981", "#ef4444"],
      },
    ],
  };

  const barData = {
    labels: ["MTTR", "Reopen %", "Breach Count"],
    datasets: [
      {
        label: "Vendor KPI",
        data: [summary.mttr_hours || 0, summary.reopen_pct, summary.breach_count],
        backgroundColor: ["#06b6d4", "#f59e0b", "#ef4444"],
      },
    ],
  };

  return (
    <div className="space-y-4">
      <div className="panel p-5 animate-rise">
        <PanelTitle
          title="Vendor Scorecard"
          subtitle="Vendor-level SLA, reliability, and service quality performance."
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {ranking.slice(0, 12).map((row) => (
            <button
              key={row.vendor}
              onClick={() => applyVendor(row.vendor)}
              className={`rounded-lg px-3 py-1 text-sm font-semibold transition ${
                row.vendor.toLowerCase() === vendorName.toLowerCase()
                  ? "bg-brand-600 text-white"
                  : "bg-slate-200 text-slate-700 hover:bg-slate-300"
              }`}
            >
              {row.vendor}
            </button>
          ))}
        </div>
      </div>

      <DateRangeFilter value={range} onChange={setRange} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <KpiCard label="Vendor" value={summary.vendor_name} />
        <KpiCard label="SLA %" value={`${summary.sla_pct}%`} tone="good" />
        <KpiCard label="MTTR (hrs)" value={summary.mttr_hours ?? "N/A"} tone="warn" />
        <KpiCard label="Reopen %" value={`${summary.reopen_pct}%`} tone="bad" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="panel p-4 animate-rise">
          <PanelTitle title="SLA Composition" />
          <Pie data={pieData} />
        </div>
        <div className="panel p-4 animate-rise">
          <PanelTitle title="Operational Metrics" />
          <Bar data={barData} />
        </div>
      </div>

      <PanelTitle title="Vendor Ranking Table" subtitle="Use this to switch context quickly." />
      <RankingTable
        rows={ranking}
        columns={[
          { key: "vendor", header: "Vendor" },
          { key: "sla_pct", header: "SLA %" },
          { key: "mttr_hours", header: "MTTR (hrs)" },
          { key: "breach_count", header: "Breaches" },
        ]}
      />

      {selectedRow ? (
        <p className="text-xs text-slate-500">Selected vendor rank snapshot loaded from executive API feed.</p>
      ) : null}
    </div>
  );
}
