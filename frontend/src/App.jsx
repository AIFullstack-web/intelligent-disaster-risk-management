import {
  Bell,
  ChevronDown,
  CircleAlert,
  CloudRain,
  LayoutDashboard,
  Map,
  Menu,
  ShieldAlert,
  Siren,
  Target,
  Users,
} from "lucide-react";

import RiskMap from "./components/RiskMap";
import "./App.css";

const metrics = [
  { label: "Monitored Assets", value: "128", icon: Target },
  { label: "Critical Risk", value: "07", icon: ShieldAlert },
  { label: "High Risk", value: "19", icon: CircleAlert },
  { label: "Open Alerts", value: "05", icon: Bell },
];

const priorityAssets = [
  {
    id: "BR-07",
    name: "Bridge BR-07",
    type: "Bridge",
    risk: "CRITICAL",
    score: "0.91",
    action: "Priority inspection",
  },
  {
    id: "RD-14",
    name: "Road Segment RD-14",
    type: "Road",
    risk: "HIGH",
    score: "0.82",
    action: "Inspect within 6h",
  },
  {
    id: "WF-03",
    name: "Water Facility WF-03",
    type: "Water Facility",
    risk: "HIGH",
    score: "0.76",
    action: "Monitor closely",
  },
];

function RiskBadge({ risk }) {
  return (
    <span className={"risk-badge risk-" + risk.toLowerCase()}>
      {risk}
    </span>
  );
}

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Siren size={20} />
          </div>

          <div>
            <div className="brand-name">INFRAguard</div>
            <div className="brand-subtitle">
              AI Risk Intelligence
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className="nav-item active">
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </button>

          <button className="nav-item">
            <Map size={18} />
            <span>Risk Map</span>
          </button>

          <button className="nav-item">
            <ShieldAlert size={18} />
            <span>Priority Assets</span>
          </button>

          <button className="nav-item">
            <Bell size={18} />
            <span>Alerts</span>
            <span className="nav-count">05</span>
          </button>

          <button className="nav-item">
            <Users size={18} />
            <span>Response Teams</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <span className="status-dot" />

            <div>
              <strong>System Online</strong>
              <span>All services operational</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu">
              <Menu size={20} />
            </button>

            <div>
              <p className="eyebrow">DISASTER INTELLIGENCE</p>
              <h1>Risk Command Center</h1>
            </div>
          </div>

          <div className="topbar-actions">
            <div className="scenario-selector">
              <span>Scenario</span>
              <strong>Extreme Rainfall</strong>
              <ChevronDown size={16} />
            </div>

            <button className="icon-button">
              <Bell size={18} />
              <span className="notification-dot" />
            </button>

            <div className="user-avatar">CK</div>
          </div>
        </header>

        <section className="page-content">
          <div className="overview-row">
            <div>
              <h2>Operational Overview</h2>

              <p>
                Current infrastructure vulnerability and inspection
                priority overview.
              </p>
            </div>

            <div className="last-updated">
              Last updated <strong>2 min ago</strong>
            </div>
          </div>

          <section className="metric-grid">
            {metrics.map((metric) => {
              const Icon = metric.icon;

              return (
                <article
                  className="metric-card"
                  key={metric.label}
                >
                  <div className="metric-icon">
                    <Icon size={18} />
                  </div>

                  <div>
                    <p>{metric.label}</p>
                    <strong>{metric.value}</strong>
                  </div>
                </article>
              );
            })}
          </section>

          <section className="dashboard-grid">
            <article className="panel map-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">
                    GEOSPATIAL MONITORING
                  </p>

                  <h3>Infrastructure Risk Map</h3>
                </div>

                <div className="map-controls">
                  <button className="filter-button active">
                    All
                  </button>

                  <button className="filter-button">
                    Critical
                  </button>

                  <button className="filter-button">
                    High
                  </button>
                </div>
              </div>

              <div className="real-map-container">
                <RiskMap />

                <div className="map-overlay">
                  <div className="map-title">
                    <Map size={17} />
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

            <article className="panel selected-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">
                    SELECTED ASSET
                  </p>

                  <h3>Bridge BR-07</h3>
                </div>

                <RiskBadge risk="CRITICAL" />
              </div>

              <div className="risk-score">
                <div className="score-ring">
                  <strong>0.91</strong>
                  <span>Risk Score</span>
                </div>

                <div className="priority-card">
                  <span>Inspection Priority</span>
                  <strong>PRIORITY INSPECTION</strong>
                </div>
              </div>

              <div className="evidence-section">
                <div className="evidence-heading">
                  <h4>Key contributing factors</h4>
                  <span>Model evidence</span>
                </div>

                <div className="factor-row">
                  <span>24h Rainfall</span>
                  <strong>182 mm</strong>
                </div>

                <div className="factor-row">
                  <span>Elevation</span>
                  <strong>12 m</strong>
                </div>

                <div className="factor-row">
                  <span>Water Proximity</span>
                  <strong>0.35 km</strong>
                </div>

                <div className="factor-row">
                  <span>Exposure</span>
                  <strong>92%</strong>
                </div>
              </div>

              <div className="recommendation">
                <CloudRain size={18} />

                <div>
                  <span>Recommended action</span>

                  <strong>
                    Inspect asset before next response cycle.
                  </strong>
                </div>
              </div>
            </article>
          </section>

          <section className="bottom-grid">
            <article className="panel priority-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">
                    DECISION SUPPORT
                  </p>

                  <h3>Inspection Priority Queue</h3>
                </div>

                <button className="text-button">
                  View all
                </button>
              </div>

              <div className="priority-list">
                {priorityAssets.map((asset) => (
                  <div
                    className="priority-item"
                    key={asset.id}
                  >
                    <div>
                      <strong>{asset.name}</strong>
                      <span>{asset.type}</span>
                    </div>

                    <div className="priority-score">
                      <strong>{asset.score}</strong>
                      <span>{asset.action}</span>
                    </div>

                    <RiskBadge risk={asset.risk} />
                  </div>
                ))}
              </div>
            </article>

            <article className="panel alerts-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">
                    EARLY WARNING
                  </p>

                  <h3>Active Alerts</h3>
                </div>

                <Bell size={18} />
              </div>

              <div className="alert-card critical-alert">
                <div className="alert-icon">
                  <ShieldAlert size={18} />
                </div>

                <div>
                  <strong>
                    Critical flood exposure
                  </strong>

                  <span>
                    3 infrastructure assets require
                    immediate review.
                  </span>
                </div>
              </div>

              <div className="alert-card warning-alert">
                <div className="alert-icon">
                  <CloudRain size={18} />
                </div>

                <div>
                  <strong>
                    Heavy rainfall detected
                  </strong>

                  <span>
                    Rainfall threshold exceeded in
                    monitored zone.
                  </span>
                </div>
              </div>

              <div className="alert-card info-alert">
                <div className="alert-icon">
                  <Target size={18} />
                </div>

                <div>
                  <strong>
                    Inspection queue updated
                  </strong>

                  <span>
                    Priority ranking recalculated 2
                    minutes ago.
                  </span>
                </div>
              </div>
            </article>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;