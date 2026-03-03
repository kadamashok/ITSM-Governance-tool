export default function KpiCard({ label, value, tone = "default" }) {
  const toneClasses =
    tone === "good"
      ? "text-emerald-700 bg-emerald-50"
      : tone === "warn"
      ? "text-amber-700 bg-amber-50"
      : tone === "bad"
      ? "text-rose-700 bg-rose-50"
      : "text-slate-800 bg-slate-50";

  return (
    <div className="panel p-4 animate-rise">
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500 font-semibold">{label}</p>
      <div className={`mt-2 inline-flex rounded-lg px-3 py-1 text-2xl font-extrabold ${toneClasses}`}>
        {value}
      </div>
    </div>
  );
}
