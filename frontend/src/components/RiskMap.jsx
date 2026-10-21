import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const riskColors = {
  CRITICAL: "#ff5d68",
  HIGH: "#ff9f43",
  MODERATE: "#f4c95d",
  LOW: "#43d69c",
};

function RiskMap({ assets, selectedId, onSelect }) {
  return (
    <MapContainer
      center={[20.35, 85.95]}
      zoom={9}
      scrollWheelZoom
      className="risk-map"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {assets.map((asset) => (
        <CircleMarker
          key={asset.id}
          center={[asset.latitude, asset.longitude]}
          radius={selectedId === asset.id ? 12 : 9}
          eventHandlers={{
            click: () => onSelect(asset),
          }}
          pathOptions={{
            color: selectedId === asset.id ? "#ffffff" : "#dbeafe",
            weight: selectedId === asset.id ? 3 : 2,
            fillColor: riskColors[asset.risk_level],
            fillOpacity: 0.9,
          }}
        >
          <Popup>
            <div className="map-popup">
              <strong>{asset.name}</strong>
              <span>{asset.asset_type}</span>
              <span>
                Risk: <b>{asset.risk_level}</b>
              </span>
              <span>
                Score: <b>{asset.risk_score.toFixed(2)}</b>
              </span>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

export default RiskMap;
