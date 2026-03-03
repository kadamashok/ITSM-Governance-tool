import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { Bar, Pie } from "react-chartjs-2";
import DateRangeFilter from "../components/DateRangeFilter";
import ErrorState from "../components/ErrorState";
import KpiCard from "../components/KpiCard";
import LoadingState from "../components/LoadingState";
import PanelTitle from "../components/PanelTitle";
import RankingTable from "../components/RankingTable";
import { getDuplicates, getGovernanceReport } from "../lib/api";

function parseError(err) {
  return err?.response?.data?.error || err?.response?.data?.detail || err?.message || "Request failed";
}

export default function GovernanceViewPage() {
  const [report, setReport] = useState(null);
  const [duplicates, setDuplicates] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [range, setRange] = useState({ startDate: "", endDate: "" });

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");
        const [gov, dup] = await Promise.all([getGovernanceReport(), getDuplicates()]);
        setReport(gov);
        setDuplicates(dup);
      } catch (err) {
        setError(parseError(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredNoUpdates = useMemo(() => {
    if (!report?.flags?.without_updates_3_plus_days) return [];
    return report.flags.without_updates_3_plus_days.filter((row) => {
      const dt = row.last_updated_at ? dayjs(row.last_updated_at) : null;
      if (!dt) return true;
      if (range.startDate && dt.isBefore(dayjs(range.startDate), "day")) return false;
      if (range.endDate && dt.isAfter(dayjs(range.endDate), "day")) return false;
      return true;
    });
  }, [report, range]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  const summary = report.summary;
  const issueBar = {
    labels: ["<2 min close", "No resolution notes", "Reopened >2", "No updates 3+ days"],
    datasets: [
      {
        label: "Flagged Tickets",
        data: [
          summary.closed_under_2_minutes,
          summary.without_resolution_notes,
          summary.reopened_more_than_2_times,
          summary.without_updates_3_plus_days,
        ],
        backgroundColor: ["#ef4444", "#f59e0b", "#0ea5e9", "#64748b"],
      },
    ],
  };

  const dupPie = {
    labels: ["Duplicates", "Unique"],
    datasets: [
      {
        data: [
          duplicates.duplicate_count,
          Math.max(0, duplicates.total_incidents_scanned - duplicates.duplicate_count),
        ],
        backgroundColor: ["#ef4444", "#10b981"],
      },
    ],
  };

  return (
    <div className="space-y-4">
      <div className="panel p-5 animate-rise">
        <PanelTitle
          title="Governance View"
          subtitle="Quality-control violations and duplicate-ticket intelligence."
        />
      </div>

      <DateRangeFilter value={range} onChange={setRange} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <KpiCard label="Incidents Scanned" value={summary.total_incidents_scanned} />
        <KpiCard label="Governance Flags" value={summary.total_flags} tone="bad" />
        <KpiCard label="Duplicate Tickets" value={duplicates.duplicate_count} tone="warn" />
        <KpiCard label="Duplicate Clusters" value={(duplicates.duplicate_clusters || []).length} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="panel p-4 animate-rise">
          <PanelTitle title="Governance Violations" />
          <Bar data={issueBar} />
        </div>
        <div className="panel p-4 animate-rise">
          <PanelTitle title="Duplicate Distribution" />
          <Pie data={dupPie} />
        </div>
      </div>

      <PanelTitle title="Stale Open Tickets (Filtered by Date)" />
      <RankingTable
        rows={filteredNoUpdates}
        columns={[
          { key: "number", header: "Ticket" },
          { key: "state", header: "State" },
          { key: "assigned_to", header: "Assigned To" },
          { key: "vendor", header: "Vendor" },
          { key: "days_since_update", header: "Days Since Update" },
        ]}
      />

      <PanelTitle title="Duplicate Clusters" />
      <RankingTable
        rows={(duplicates.duplicate_clusters || []).map((x) => ({
          cluster_id: x.cluster_id,
          size: x.size,
          incidents: x.members.map((m) => m.number).join(", "),
        }))}
        columns={[
          { key: "cluster_id", header: "Cluster" },
          { key: "size", header: "Size" },
          { key: "incidents", header: "Incident Numbers" },
        ]}
      />
    </div>
  );
}
