export default function ErrorState({ message }) {
  return (
    <div className="panel p-8 text-center animate-rise">
      <p className="text-sm font-semibold text-rose-700">Unable to load dashboard</p>
      <p className="mt-1 text-sm text-slate-600">{message}</p>
    </div>
  );
}
