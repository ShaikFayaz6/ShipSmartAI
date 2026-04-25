const CARRIER_COLORS = {
  FedEx: { bg: "#4D148C", accent: "#FF6600", label: "FedEx" },
  UPS: { bg: "#351C15", accent: "#FFB500", label: "UPS" },
  USPS: { bg: "#004B87", accent: "#E31837", label: "USPS" },
};

function CarrierBadge({ carrier }) {
  const c = CARRIER_COLORS[carrier] || { bg: "#333", accent: "#fff", label: carrier };
  return (
    <span
      className="carrier-badge"
      style={{ background: c.bg, borderColor: c.accent }}
    >
      {c.label}
    </span>
  );
}

function QuoteRow({ quote, isRecommended }) {
  const sourceLabel = quote.notes?.includes("Shippo")
    ? "Shippo API"
    : quote.notes?.includes("FedEx")
      ? "FedEx API"
      : "Carrier API";

  return (
    <tr className={`quote-row ${isRecommended ? "quote-row--best" : ""}`}>
      <td>
        <CarrierBadge carrier={quote.carrier} />
      </td>
      <td>
        <span className="service-name">{quote.service_name}</span>
        {isRecommended && <span className="best-tag">Best Value</span>}
      </td>
      <td className="cost-cell">${quote.estimated_cost.toFixed(2)}</td>
      <td>
        <span className={`days-chip days-chip--${quote.estimated_days <= 1 ? "fast" : quote.estimated_days <= 3 ? "mid" : "slow"}`}>
          {quote.estimated_days} day{quote.estimated_days > 1 ? "s" : ""}
        </span>
      </td>
      <td className="weight-cell">{quote.billable_weight} lbs</td>
      <td>
        {quote.guaranteed ? (
          <span className="guarantee guarantee--yes">✓ Yes</span>
        ) : (
          <span className="guarantee guarantee--no">— No</span>
        )}
      </td>
      <td>
        <span className="source-chip">{sourceLabel}</span>
      </td>
      <td className="notes-cell">{quote.notes || "—"}</td>
    </tr>
  );
}

export default function ResultsTable({ data }) {
  const { quotes, recommended, ai_summary, origin_zip, destination_zip, actual_weight, carrier_warnings = [] } = data;

  return (
    <div className="results-section">
      {/* AI Summary Banner */}
      <div className="ai-summary">
        <div className="ai-summary-icon">🤖</div>
        <div>
          <p className="ai-summary-label">AI Recommendation</p>
          <p className="ai-summary-text">{ai_summary}</p>
        </div>
      </div>

      {/* Meta info */}
      <div className="results-meta">
        <span>📍 {origin_zip} → {destination_zip}</span>
        <span>⚖ Actual weight: {actual_weight} lbs</span>
        <span>📋 {quotes.length} options found</span>
      </div>

      {carrier_warnings.length > 0 && (
        <div className="carrier-warnings">
          {carrier_warnings.map((w, idx) => (
            <div className="carrier-warning" key={`${w.carrier}-${idx}`}>
              <strong>{w.carrier}:</strong> {w.message}
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="table-wrap">
        <table className="quotes-table">
          <thead>
            <tr>
              <th>Carrier</th>
              <th>Service</th>
              <th>Cost</th>
              <th>Transit</th>
              <th>Billable Wt.</th>
              <th>Guaranteed</th>
              <th>Source</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {quotes.map((q, i) => (
              <QuoteRow
                key={i}
                quote={q}
                isRecommended={
                  recommended &&
                  q.carrier === recommended.carrier &&
                  q.service_name === recommended.service_name
                }
              />
            ))}
          </tbody>
        </table>
      </div>

      {quotes.length === 0 && (
        <div className="no-results">
          No carriers found matching your delivery deadline. Try increasing the delivery days.
        </div>
      )}
    </div>
  );
}
