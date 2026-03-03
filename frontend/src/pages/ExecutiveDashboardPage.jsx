import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { Bar, Line, Pie } from "react-chartjs-2";
import DateRangeFilter from "../components/DateRangeFilter";
import ErrorState from "../components/ErrorState";
import KpiCard from "../components/KpiCard";
import LoadingState from "../components/LoadingState";
import PanelTitle from "../components/PanelTitle";
import RankingTable from "../components/RankingTable";
import ReviewPeriodSelect from "../components/ReviewPeriodSelect";
import { getExecutiveDashboard } from "../lib/api";

function parseError(err) {
  return err?.response?.data?.error || err?.response?.data?.detail || err?.message || "Request failed";
}

export default function ExecutiveDashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [range, setRange] = useState({ startDate: "", endDate: "" });
  const [period, setPeriod] = useState("1d");
  const [fetchMessage, setFetchMessage] = useState("");
  const periodLabelMap = {
    "30m": "30 minutes",
    "1h": "1 hour",
    "3h": "3 hours",
    "8h": "8 hours",
    "1d": "1 day",
    "5d": "5 days",
    "10d": "10 days",
    "15d": "15 days",
  };

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");
        setFetchMessage(`Fetching data for last ${periodLabelMap[period] || period} period...`);
        const res = await getExecutiveDashboard(period, 1, 25);
        setData(res.data);
      } catch (err) {
        setError(parseError(err));
      } finally {
        setFetchMessage("");
        setLoading(false);
      }
    }
    load();
  }, [period]);

  const filteredTrend = useMemo(() => {
    if (!data?.breach_trend) return [];
    return data.breach_trend.filter((point) => {
      const d = dayjs(point.date);
      if (range.startDate && d.isBefore(dayjs(range.startDate), "day")) return false;
      if (range.endDate && d.isAfter(dayjs(range.endDate), "day")) return false;
      return true;
    });
  }, [data, range]);

  if (loading && !data) return <LoadingState />;
  if (error && !data) return <ErrorState message={error} />;

  const trendData = {
    labels: filteredTrend.map((x) => dayjs(x.date).format("DD MMM")),
    datasets: [
      {
        label: "Breaches",
        data: filteredTrend.map((x) => x.breach_count),
        borderColor: "#0f766e",
        backgroundColor: "rgba(15, 118, 110, 0.15)",
        fill: true,
        tension: 0.3,
      },
    ],
  };

  const rankingData = {
    labels: (data.vendor_ranking || []).map((x) => x.vendor),
    datasets: [
      {
        label: "SLA %",
        data: (data.vendor_ranking || []).map((x) => x.sla_pct),
        backgroundColor: "#06b6d4",
      },
    ],
  };

  const pieData = {
    labels: (data.vendor_ranking || []).slice(0, 5).map((x) => x.vendor),
    datasets: [
      {
        label: "Breach Count",
        data: (data.vendor_ranking || []).slice(0, 5).map((x) => x.breach_count),
        backgroundColor: ["#ef4444", "#f59e0b", "#0ea5e9", "#10b981", "#8b5cf6"],
      },
    ],
  };

  return (
    <div className="space-y-4">
      <div className="panel p-5 animate-rise">
        <PanelTitle
          title="Executive Dashboard"
          subtitle="High-level SLA health, open workload, breach trajectory, and vendor performance."
        />
      </div>

      <DateRangeFilter value={range} onChange={setRange} />
      <ReviewPeriodSelect value={period} disabled={loading} onChange={setPeriod} />
      {fetchMessage ? <p className="text-sm text-slate-600">{fetchMessage}</p> : null}
      {error ? <ErrorState message={error} /> : null}
      {data?.vendor_ranking?.length === 0 ? (
        <div className="panel p-5 text-sm text-slate-600">No data found for selected period.</div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard label="Overall SLA" value={`${data.overall_sla_pct}%`} tone="good" />
        <KpiCard label="Open Tickets" value={data.total_open_tickets} tone="warn" />
        <KpiCard label="Ranked Vendors" value={(data.vendor_ranking || []).length} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="panel p-4 animate-rise">
          <PanelTitle title="Breach Trend" subtitle="Daily trend for the selected range" />
          <Line data={trendData} />
        </div>
        <div className="panel p-4 animate-rise">
          <PanelTitle title="Top Vendor Breaches" subtitle="Distribution across top 5 vendors" />
          <Pie data={pieData} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="panel p-4 animate-rise">
          <PanelTitle title="Vendor SLA Ranking" subtitle="Sorted by SLA adherence" />
          <Bar data={rankingData} />
        </div>
        <div>
          <PanelTitle title="Ranking Table" />
          <RankingTable
            rows={data.vendor_ranking || []}
            columns={[
              { key: "vendor", header: "Vendor" },
              { key: "sla_pct", header: "SLA %" },
              { key: "mttr_hours", header: "MTTR (hrs)" },
              { key: "breach_count", header: "Breaches" },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
