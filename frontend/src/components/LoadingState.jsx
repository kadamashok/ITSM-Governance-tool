export default function LoadingState({ message = "Loading dashboard data..." }) {
  return (
    <div className="panel p-8 text-center animate-rise">
      <div className="mx-auto h-7 w-7 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      <p className="mt-3 text-sm text-slate-600">{message}</p>
    </div>
  );
}
