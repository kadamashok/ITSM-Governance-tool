export default function PanelTitle({ title, subtitle }) {
  return (
    <div className="mb-3">
      <h2 className="section-title">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
    </div>
  );
}
