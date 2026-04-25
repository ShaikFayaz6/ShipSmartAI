import { useState } from "react";
import ShippingForm from "./components/ShippingForm";
import ResultsTable from "./components/ResultsTable";
import "./index.css";

export default function App() {
  const [quotes, setQuotes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apiBaseUrl = import.meta.env.VITE_API_URL || "/api";

  const handleSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    setQuotes(null);

    try {
      const res = await fetch(`${apiBaseUrl}/api/rates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Server error");
      }

      const data = await res.json();
      setQuotes(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo-mark">✦</div>
          <div>
            <h1 className="app-title">ShipSmart<span className="accent"> AI</span></h1>
            <p className="app-subtitle">Multi-carrier rate comparison · Powered by AI agents</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <ShippingForm onSubmit={handleSubmit} loading={loading} />

        {error && (
          <div className="error-banner">
            <span>⚠</span> {error}
          </div>
        )}

        {loading && (
          <div className="loading-state">
            <div className="spinner-ring" />
            <div className="loading-text">
              <p className="loading-primary">Querying carriers...</p>
              <p className="loading-secondary">FedEx · UPS · USPS agents running in parallel</p>
            </div>
          </div>
        )}

        {quotes && !loading && <ResultsTable data={quotes} />}
      </main>

      <footer className="app-footer">
        ShipSmart AI · Multi-Agent Architecture · FedEx REST + UPS + USPS
      </footer>
    </div>
  );
}
