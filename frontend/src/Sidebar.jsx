function QualitySection({ title, report }) {
  if (!report) return null;
  return (
    <div className="quality-section">
      <div className="quality-section-title">
        {report.board} <span className="quality-row-count">{report.row_count} rows</span>
      </div>
      {report.notes.length === 0 ? (
        <p className="quality-note quality-note-clean">No issues flagged.</p>
      ) : (
        <ul className="quality-notes">
          {report.notes.map((note, i) => (
            <li key={i}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Sidebar({ health, quality, onRefresh, refreshing }) {
  return (
    <aside className="sidebar">
      <h2>Data source</h2>
      {health ? (
        <div className={`mode-banner ${health.monday_mode === "live" ? "mode-live" : "mode-mock"}`}>
          {health.monday_mode === "live"
            ? "Connected to live monday.com boards"
            : "Running on local mock data (fixtures/) — no monday.com credentials configured."}
        </div>
      ) : (
        <div className="mode-banner">Checking connection…</div>
      )}

      <button className="refresh-button" onClick={onRefresh} disabled={refreshing}>
        {refreshing ? "Refreshing…" : "Refresh data from monday.com"}
      </button>

      <h2>Data quality report</h2>
      {quality ? (
        <>
          <QualitySection report={quality.work_orders} />
          <QualitySection report={quality.deals} />
          {quality.cross_board_notes.length > 0 && (
            <div className="quality-section">
              <div className="quality-section-title">Cross-board</div>
              <ul className="quality-notes">
                {quality.cross_board_notes.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      ) : (
        <p className="quality-note">Loading…</p>
      )}
    </aside>
  );
}
