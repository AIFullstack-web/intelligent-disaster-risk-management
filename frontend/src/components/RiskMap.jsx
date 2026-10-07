import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

const assets = [
  {
    id: "BR-07",
    name: "Bridge BR-07",
    type: "Bridge",
    risk: "CRITICAL",
    score: 0.91,
    position: [20.2961, 85.8245],
  },
  {
    id: "RD-14",
    name: "Road Segment RD-14",
    type: "Road",
    risk: "HIGH",
    score: 0.82,
    position: [20.4625, 85.883],
  },
  {
    id: "WF-03",
    name: "Water Facility WF-03",
    type: "Water Facility",
    risk: "HIGH",
    score: 0.76,
    position: [20.271, 86.693],
  },
  {
    id: "A-02",
    name: "Infrastructure Asset A-02",
    type: "Infrastructure",
    risk: "MODERATE",
    score: 0.43,
    position: [20.26, 85.82],
  },
  {
    id: "M-01",
    name: "Monitoring Zone M-01",
    type: "Monitoring",
    risk: "LOW",
    score: 0.19,
    position: [20.49, 85.62],
  },
];

const riskColors = {
  CRITICAL: "#ff5d68",
  HIGH: "#ff9f43",
  MODERATE: "#f4c95d",
  LOW: "#43d69c",
};

function RiskMap() {
  return (
    <MapContainer
      center={[20.35, 85.95]}
      zoom={9}
      scrollWheelZoom
      className="risk-map"
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {assets.map((asset) => (
        <CircleMarker
          key={asset.id}
          center={asset.position}
          radius={9}
          pathOptions={{
            color: "#ffffff",
            weight: 2,
            fillColor: riskColors[asset.risk],
            fillOpacity: 0.9,
          }}
        >
          <Popup>
            <div>
              <strong>{asset.name}</strong>
              <br />
              <span>{asset.type}</span>
              <br />
              <span>Risk: {asset.risk}</span>
              <br />
              <span>Score: {asset.score.toFixed(2)}</span>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

export default RiskMap;
