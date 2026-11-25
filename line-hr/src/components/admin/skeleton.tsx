/** Placeholder shown while a page's session-dependent content streams in. */
export function ContentSkeleton({ tiles = false, rows = 3 }: { tiles?: boolean; rows?: number }) {
  return (
    <div className="animate-pulse space-y-3" aria-busy aria-label="กำลังโหลด">
      {tiles && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="h-24 rounded-2xl bg-slate-200" />
          ))}
        </div>
      )}
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-28 rounded-2xl bg-slate-200" />
      ))}
    </div>
  );
}
