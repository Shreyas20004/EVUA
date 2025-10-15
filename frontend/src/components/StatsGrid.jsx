export default function StatsCard({ label, value, hint }) {
  return (
    <div className="bg-evua-panel rounded-xl border border-border/20 shadow-lg p-4">
      <div className="flex items-center justify-between">
        <p className="text-evua-muted text-sm">{label}</p>
      </div>
      <p className="text-evua-foreground text-2xl font-semibold mt-1">{value}</p>
      {hint ? <p className="text-evua-muted text-xs mt-2">{hint}</p> : null}
    </div>
  )
}
