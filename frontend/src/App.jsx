import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  CloudRain,
  LayoutDashboard,
  Map,
  Menu,
  RefreshCw,
  ShieldAlert,
  Siren,
  Target,
  Users,
  X,
} from "lucide-react";

import RiskMap from "./components/RiskMap";
import {
  API_BASE_URL,
  getAlerts,
  getHealth,
  getMetadata,
  getPriorities,
  getRisks,
} from "./api";
import "./App.css";

const fallbackAssets = [
  {
    id: "BR-07",
    name: "Bridge BR-07",
    asset_type: "Bridge",
    latitude: 20.2961,
    longitude: 85.8245,
    risk_score: 0.91,
    risk_level: "CRITICAL",
    priority_score: 0.95,
    rainfall_24h_mm: 182,
    elevation_m: 12,
    water_distance_km: 0.35,
    exposure: 0.92,
    recommended_action:
      "Priority inspection before the next response cycle.",
  },
  {
    id: "RD-14",
    name: "Road Segment RD-14",
    asset_type: "Road",
    latitude: 20.4625,
    longitude: 85.883,
    risk_score: 0.82,
    risk_level: "HIGH",
    priority_score: 0.86,
    rainfall_24h_mm: 145,
    elevation_m: 19,
    water_distance_km: 0.62,
    exposure: 0.79,
    recommended_action: "Inspect within the next 6 hours.",
  },
  {
    id: "WF-03",
    name: "Water Facility WF-03",
    asset_type: "Water Facility",
    latitude: 20.271,
    longitude: 86.693,
    risk_score: 0.76,
    risk_level: "HIGH",
    priority_score: 0.79,
    rainfall_24h_mm: 121,
    elevation_m: 24,
    water_distance_km: 0.85,
    exposure: 0.74,
    recommended_action:
      "Monitor closely and prepare inspection resources.",
  },
  {
    id: "A-02",
    name: "Infrastructure Asset A-02",
    asset_type: "Infrastructure",
    latitude: 20.26,
    longitude: 85.82,
    risk_score: 0.43,
    risk_level: "MODERATE",
    priority_score: 0.44,
    rainfall_24h_mm: 82,
    elevation_m: 38,
    water_distance_km: 1.4,
    exposure: 0.55,
    recommended_action:
      "Continue monitoring under the selected scenario.",
  },
  {
    id: "M-01",
    name: "Monitoring Zone M-01",
    asset_type: "Monitoring",
    latitude: 20.49,
    longitude: 85.62,
    risk_score: 0.19,
    risk_level: "LOW",
    priority_score: 0.2,
    rainfall_24h_mm: 41,
    elevation_m: 64,
    water_distance_km: 3.1,
    exposure: 0.28,
    recommended_action: "Routine monitoring.",
  },
];

const fallbackAlerts = [
  {
    id: "ALERT-001",
    severity: "CRITICAL",
    title: "Critical flood exposure",
    message: "1 asset requires priority inspection.",
  },
  {
    id: "ALERT-002",
    severity: "HIGH",
    title: "Heavy rainfall detected",
    message: "2 high-risk assets are under elevated exposure.",
  },
  {
    id: "ALERT-003",
    severity: "INFO",
    title: "Inspection queue updated",
    message: "Priority rankings were recalculated.",
  },
];

const views = {
  dashboard: {
    title: "Risk Command Center",
    description:
      "Current infrastructure vulnerability and inspection priority overview.",
  },
  map: {
    title: "Interactive Risk Map",
    description:
      "Explore monitored infrastructure and select an asset for detailed risk evidence.",
  },
  priority: {
    title: "Priority Assets",
    description:
      "Review the assets that should receive earlier inspection attention.",
  },
  alerts: {
    title: "Alert Center",
    description:
      "Review early-warning events generated from the current scenario.",
  },
  teams: {
    title: "Response Teams",
    description:
      "Operational coordination view for inspection and emergency response planning.",
  },
};

function RiskBadge({ risk }) {
  return (
    <span className={"risk-badge risk-" + risk.toLowerCase()}>
      {risk}
    </span>
  );
}

function App() {
  const [assets, setAssets] = useState(fallbackAssets);
  const [alerts, setAlerts] = useState(fallbackAlerts);
  const [activeView, setActiveView] = useState("dashboard");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [selectedAsset, setSelectedAsset] = useState(fallbackAssets[0]);
  const [scenario, setScenario] = useState("Extreme Rainfall");
  const [apiOnline, setApiOnline] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("Demo data");

  async function loadData() {
    setLoading(true);

    try {
      const [health, risks, priorities, alertData, meta] =
        await Promise.all([
          getHealth(),
          getRisks(),
          getPriorities(),
          getAlerts(),
          getMetadata(),
        ]);

      if (health?.status === "ok") {
        setApiOnline(true);
      }

      if (risks?.length) {
        setAssets(risks);
        setSelectedAsset(
          risks.find((item) => item.id === selectedAsset.id) || risks[0],
        );
      }

      if (priorities?.length) {
        setAssets((current) =>
          current.map(
            (item) =>
              priorities.find((priority) => priority.id === item.id) ||
              item,
          ),
        );
      }

      if (alertData?.length) {
        setAlerts(alertData);
      }

      setMetadata(meta);
      setLastUpdated(new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }));
    } catch {
      setApiOnline(false);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const filteredAssets = useMemo(() => {
    if (riskFilter === "ALL") return assets;
    return assets.filter((asset) => asset.risk_level === riskFilter);
  }, [assets, riskFilter]);

  const counts = useMemo(
    () => ({
      total: assets.length,
      critical: assets.filter((a) => a.risk_level === "CRITICAL").length,
      high: assets.filter((a) => a.risk_level === "HIGH").length,
      moderate: assets.filter((a) => a.risk_level === "MODERATE").length,
      low: assets.filter((a) => a.risk_level === "LOW").length,
    }),
    [assets],
  );

  const priorities = useMemo(
    () =>
      [...assets].sort(
        (a, b) => b.priority_score - a.priority_score,
      ),
    [assets],
  );

  const navItems = [
    ["dashboard", LayoutDashboard, "Dashboard"],
    ["map", Map, "Risk Map"],
    ["priority", ShieldAlert, "Priority Assets"],
    ["alerts", Bell, "Alerts"],
    ["teams", Users, "Response Teams"],
  ];

  const view = views[activeView];

  function selectAsset(asset) {
    setSelectedAsset(asset);
    if (activeView === "map") {
      setActiveView("dashboard");
    }
  }

  return (
    <div className="app-shell">
      <aside className={"sidebar " + (mobileOpen ? "sidebar-open" : "")}>
        <div className="brand">
          <div className="brand-mark">
            <Siren size={20} />
          </div>

          <div>
            <div className="brand-name">INFRAguard</div>
            <div className="brand-subtitle">AI Risk Intelligence</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(([id, Icon, label]) => (
            <button
              className={"nav-item " + (activeView === id ? "active" : "")}
              key={id}
              onClick={() => {
                setActiveView(id);
                setMobileOpen(false);
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === "alerts" && (
                <span className="nav-count">{alerts.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <span
              className={
                "status-dot " + (apiOnline ? "" : "status-offline")
              }
            />

            <div>
              <strong>
                {apiOnline ? "API Connected" : "Demo Mode"}
              </strong>
              <span>{apiOnline ? API_BASE_URL : "Local fallback data"}</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu"
              onClick={() => setMobileOpen((open) => !open)}
            >
              <Menu size={20} />
            </button>

            <div>
              <p className="eyebrow">DISASTER INTELLIGENCE</p>
              <h1>{view.title}</h1>
            </div>
          </div>

          <div className="topbar-actions">
            <label className="scenario-selector">
              <span>Scenario</span>

              <select
                value={scenario}
                onChange={(event) =>
                  setScenario(event.target.value)
                }
              >
                <option>Extreme Rainfall</option>
                <option>Flood-related Conditions</option>
                <option>Monitoring Scenario</option>
              </select>

              <ChevronDown size={16} />
            </label>

            <button
              className="icon-button"
              onClick={() => setActiveView("alerts")}
              aria-label="Open alerts"
            >
              <Bell size={18} />
              <span className="notification-dot" />
            </button>

            <div className="user-avatar">CK</div>
          </div>
        </header>

        <section className="page-content">
          <div className="overview-row">
            <div>
              <div className="title-line">
                <h2>{view.title}</h2>
                <span className="demo-badge">
                  {metadata?.engine || "demo-rule-based"}
                </span>
              </div>

              <p>{view.description}</p>
            </div>

            <button
              className="refresh-button"
              onClick={loadData}
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? "spin" : ""} />
              Refresh
            </button>
          </div>

          {activeView === "dashboard" && (
            <>
              <section className="metric-grid">
                <MetricCard
                  label="Monitored Assets"
                  value={counts.total}
                  icon={Target}
                />

                <MetricCard
                  label="Critical Risk"
                  value={counts.critical}
                  icon={ShieldAlert}
                />

                <MetricCard
                  label="High Risk"
                  value={counts.high}
                  icon={CircleAlert}
                />

                <MetricCard
                  label="Open Alerts"
                  value={alerts.length}
                  icon={Bell}
                />
              </section>

              <section className="dashboard-grid">
                <MapPanel
                  assets={filteredAssets}
                  selectedAsset={selectedAsset}
                  riskFilter={riskFilter}
                  setRiskFilter={setRiskFilter}
                  onSelect={selectAsset}
                />

                <AssetDetails asset={selectedAsset} />
              </section>

              <section className="bottom-grid">
                <PriorityPanel
                  assets={priorities}
                  onSelect={selectAsset}
                  onViewAll={() => setActiveView("priority")}
                />

                <AlertsPanel
                  alerts={alerts}
                  onViewAll={() => setActiveView("alerts")}
                />
              </section>
            </>
          )}

          {activeView === "map" && (
            <section className="single-view-panel panel">
              <div className="map-page-header">
                <div className="map-filter-row">
                  {["ALL", "CRITICAL", "HIGH", "MODERATE", "LOW"].map(
                    (filter) => (
                      <button
                        key={filter}
                        className={
                          "filter-button " +
                          (riskFilter === filter ? "active" : "")
                        }
                        onClick={() => setRiskFilter(filter)}
                      >
                        {filter}
                      </button>
                    ),
                  )}
                </div>
              </div>

              <div className="full-map">
                <RiskMap
                  assets={filteredAssets}
                  selectedId={selectedAsset?.id}
                  onSelect={selectAsset}
                />
              </div>
            </section>
          )}

          {activeView === "priority" && (
            <PriorityPage
              assets={priorities}
              selectedId={selectedAsset?.id}
              onSelect={selectAsset}
            />
          )}

          {activeView === "alerts" && (
            <AlertsPage
              alerts={alerts}
              assets={assets}
              onSelect={selectAsset}
            />
          )}

          {activeView === "teams" && <TeamsPage />}
        </section>
      </main>
    </div>
  );
}

function MetricCard({ label, value, icon: Icon }) {
  return (
    <article className="metric-card">
      <div className="metric-icon">
        <Icon size={18} />
      </div>

      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function MapPanel({
  assets,
  selectedAsset,
  riskFilter,
  setRiskFilter,
  onSelect,
}) {
  return (
    <article className="panel map-panel">
      <div className="panel-header">
        <div>
          <p className="section-label">GEOSPATIAL MONITORING</p>
          <h3>Infrastructure Risk Map</h3>
        </div>

        <div className="map-controls">
          {["ALL", "CRITICAL", "HIGH"].map((filter) => (
            <button
              className={
                "filter-button " +
                (riskFilter === filter ? "active" : "")
              }
              key={filter}
              onClick={() => setRiskFilter(filter)}
            >
              {filter === "ALL" ? "All" : filter}
            </button>
          ))}
        </div>
      </div>

      <div className="real-map-container">
        <RiskMap
          assets={assets}
          selectedId={selectedAsset?.id}
          onSelect={onSelect}
        />

        <div className="map-overlay">
          <div className="map-title">
            <Map size={16} />
            <span>GIS Risk Intelligence Layer</span>
          </div>

          <div className="map-legend">
            <span>
              <i className="legend-dot critical" />
              Critical
            </span>
            <span>
              <i className="legend-dot high" />
              High
            </span>
            <span>
              <i className="legend-dot moderate" />
              Moderate
            </span>
            <span>
              <i className="legend-dot low" />
              Low
            </span>
          </div>
        </div>
      </div>
    </article>
  );
}

function AssetDetails({ asset }) {
  if (!asset) return null;

  return (
    <article className="panel selected-panel">
      <div className="panel-header">
        <div>
          <p className="section-label">SELECTED ASSET</p>
          <h3>{asset.name}</h3>
        </div>

        <RiskBadge risk={asset.risk_level} />
      </div>

      <div className="asset-type">{asset.asset_type}</div>

      <div className="risk-score">
        <div className="score-ring">
          <strong>{asset.risk_score.toFixed(2)}</strong>
          <span>Risk Score</span>
        </div>

        <div className="priority-card">
          <span>Inspection Priority</span>
          <strong>
            {asset.priority_score >= 0.8
              ? "PRIORITY INSPECTION"
              : "MONITOR"}
          </strong>

          <small>
            Priority score {asset.priority_score.toFixed(2)}
          </small>
        </div>
      </div>

      <div className="evidence-section">
        <div className="evidence-heading">
          <h4>Key contributing factors</h4>
          <span>Current record</span>
        </div>

        <FactorRow
          label="24h Rainfall"
          value={asset.rainfall_24h_mm + " mm"}
        />

        <FactorRow
          label="Elevation"
          value={asset.elevation_m + " m"}
        />

        <FactorRow
          label="Water Proximity"
          value={asset.water_distance_km + " km"}
        />

        <FactorRow
          label="Exposure"
          value={Math.round(asset.exposure * 100) + "%"}
        />
      </div>

      <div className="recommendation">
        <CloudRain size={18} />

        <div>
          <span>Recommended action</span>
          <strong>{asset.recommended_action}</strong>
        </div>
      </div>
    </article>
  );
}

function FactorRow({ label, value }) {
  return (
    <div className="factor-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PriorityPanel({ assets, onSelect, onViewAll }) {
  return (
    <article className="panel priority-panel">
      <div className="panel-header">
        <div>
          <p className="section-label">DECISION SUPPORT</p>
          <h3>Inspection Priority Queue</h3>
        </div>

        <button className="text-button" onClick={onViewAll}>
          View all
        </button>
      </div>

      <div className="priority-list">
        {assets.slice(0, 4).map((asset) => (
          <button
            className="priority-item"
            key={asset.id}
            onClick={() => onSelect(asset)}
          >
            <div>
              <strong>{asset.name}</strong>
              <span>{asset.asset_type}</span>
            </div>

            <div className="priority-score">
              <strong>{asset.risk_score.toFixed(2)}</strong>
              <span>Priority {asset.priority_score.toFixed(2)}</span>
            </div>

            <RiskBadge risk={asset.risk_level} />
          </button>
        ))}
      </div>
    </article>
  );
}

function AlertsPanel({ alerts, onViewAll }) {
  return (
    <article className="panel alerts-panel">
      <div className="panel-header">
        <div>
          <p className="section-label">EARLY WARNING</p>
          <h3>Active Alerts</h3>
        </div>

        <button className="icon-only-button" onClick={onViewAll}>
          <Bell size={16} />
        </button>
      </div>

      {alerts.slice(0, 3).map((alert) => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </article>
  );
}

function AlertCard({ alert }) {
  const Icon =
    alert.severity === "CRITICAL"
      ? ShieldAlert
      : alert.severity === "HIGH"
        ? CloudRain
        : CheckCircle2;

  return (
    <div className={"alert-card " + alert.severity.toLowerCase() + "-alert"}>
      <div className="alert-icon">
        <Icon size={17} />
      </div>

      <div>
        <strong>{alert.title}</strong>
        <span>{alert.message}</span>
      </div>
    </div>
  );
}

function PriorityPage({ assets, selectedId, onSelect }) {
  return (
    <section className="panel page-panel">
      <div className="page-panel-header">
        <div>
          <p className="section-label">SORTED BY PRIORITY SCORE</p>
          <h3>Inspection queue</h3>
        </div>
      </div>

      <div className="table">
        <div className="table-row table-head">
          <span>Asset</span>
          <span>Risk</span>
          <span>Risk Score</span>
          <span>Priority</span>
          <span>Action</span>
        </div>

        {assets.map((asset) => (
          <button
            className={
              "table-row " +
              (asset.id === selectedId ? "selected-row" : "")
            }
            key={asset.id}
            onClick={() => onSelect(asset)}
          >
            <span>
              <strong>{asset.name}</strong>
              <small>{asset.asset_type}</small>
            </span>

            <RiskBadge risk={asset.risk_level} />

            <strong>{asset.risk_score.toFixed(2)}</strong>

            <strong>{asset.priority_score.toFixed(2)}</strong>

            <span>{asset.recommended_action}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function AlertsPage({ alerts, assets }) {
  return (
    <section className="alerts-page">
      <div className="alert-summary">
        <div className="summary-card critical">
          <span>Critical assets</span>
          <strong>
            {assets.filter((a) => a.risk_level === "CRITICAL").length}
          </strong>
        </div>

        <div className="summary-card high">
          <span>High-risk assets</span>
          <strong>
            {assets.filter((a) => a.risk_level === "HIGH").length}
          </strong>
        </div>

        <div className="summary-card info">
          <span>Active alerts</span>
          <strong>{alerts.length}</strong>
        </div>
      </div>

      <section className="panel page-panel">
        <div className="page-panel-header">
          <div>
            <p className="section-label">EARLY WARNING</p>
            <h3>Alert Center</h3>
          </div>
        </div>

        <div className="alerts-page-list">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      </section>
    </section>
  );
}

function TeamsPage() {
  return (
    <section className="teams-grid">
      <div className="team-hero panel">
        <div className="hero-icon">
          <Users size={24} />
        </div>

        <p className="section-label">RESPONSE COORDINATION</p>
        <h3>Inspection and emergency response support</h3>

        <p>
          This view is prepared for coordinating inspection resources
          around the highest-priority assets. Team assignment and live
          field telemetry can be connected after the risk pipeline is
          integrated with operational data.
        </p>

        <div className="team-status-row">
          <span>
            <i className="legend-dot low" />
            Planning workspace ready
          </span>

          <span>
            <Target size={14} />
            Priority queue available
          </span>
        </div>
      </div>

      <div className="panel team-checklist">
        <p className="section-label">RESPONSE PLAYBOOK</p>
        <h3>Suggested workflow</h3>

        {[
          "Review critical assets",
          "Assign inspection resources",
          "Validate local conditions",
          "Record field findings",
        ].map((step, index) => (
          <div className="check-item" key={step}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{step}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export default App;
