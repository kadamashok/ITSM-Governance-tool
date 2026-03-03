const PERIOD_OPTIONS = [
  { label: "Last 30 Minutes", value: "30m" },
  { label: "Last 1 Hour", value: "1h" },
  { label: "Last 3 Hours", value: "3h" },
  { label: "Last 8 Hours", value: "8h" },
  { label: "Last 1 Day", value: "1d" },
  { label: "Last 5 Days", value: "5d" },
  { label: "Last 10 Days", value: "10d" },
  { label: "Last 15 Days", value: "15d" },
];

export default function ReviewPeriodSelect({ value, disabled, onChange }) {
  return (
    <div className="panel p-4 animate-rise">
      <label className="text-sm font-semibold text-slate-700">
        Data Review Period
        <select
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-brand-500 disabled:cursor-not-allowed disabled:bg-slate-100"
        >
          {PERIOD_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {value === "15d" ? (
        <p className="mt-2 text-xs font-semibold text-amber-700">
          Large data range may take longer time.
        </p>
      ) : null}
    </div>
  );
}
