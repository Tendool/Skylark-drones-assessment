import { RefreshIcon } from "./icons.jsx";

function SkeletonBlock() {
  return (
    <div className="quality-section skeleton-block">
      <div className="skeleton-line" style={{ width: "40%" }} />
      <div className="skeleton-line" style={{ width: "95%" }} />
      <div className="skeleton-line" style={{ width: "80%" }} />
    </div>
  );
}

function QualitySection({ report }) {
  if (!report) return null;
  return (
    <div className="quality-section">
      <div className="quality-section-title">
        <span>{report.board}</span>
        <span className="quality-row-count">{report.row_count} rows</span>
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
  const mode = health?.monday_mode;
  const statusClass = !health ? "status-pending" : mode === "live" ? "status-live" : "status-mock";
  const statusLabel = !health
    ? "Checking connection…"
    : mode === "live"
      ? "Connected to live monday.com boards"
      : "Mock data (fixtures/) — no monday.com credentials configured";

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-logo-wrap">
          <img src="/skylark-drones-logo.png" alt="Skylark Drones" className="brand-logo" />
        </div>
        <div className="brand-tagline">Business Intelligence Agent</div>
      </div>

      <div className="sidebar-body">
        <h2>Data source</h2>
        <div className={`status-pill ${statusClass}`}>
          <span className="dot" />
          <span>{statusLabel}</span>
        </div>

        <button className="ghost-button" onClick={onRefresh} disabled={refreshing}>
          <RefreshIcon spinning={refreshing} />
          {refreshing ? "Refreshing…" : "Refresh data"}
        </button>

        <h2>Data quality report</h2>
        {quality ? (
          <>
            <QualitySection report={quality.work_orders} />
            <QualitySection report={quality.deals} />
            {quality.cross_board_notes.length > 0 && (
              <div className="quality-section">
                <div className="quality-section-title">
                  <span>Cross-board</span>
                </div>
                <ul className="quality-notes">
                  {quality.cross_board_notes.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <>
            <SkeletonBlock />
            <SkeletonBlock />
          </>
        )}
      </div>

      <div className="sidebar-footer">
        <div>Work Orders + Deals boards · read-only</div>
        <div className="sidebar-credit">
          Made by{" "}
          <a href="https://tendool.me/" target="_blank" rel="noopener noreferrer">
            Tendool Srivatsav Sala
          </a>
        </div>
      </div>
    </aside>
  );
}
