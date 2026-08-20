import { useEffect, useMemo } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const MAURITIUS_CENTER = [-20.28, 57.55];
const DEFAULT_ZOOM = 10;

function FitMauritius() {
  const map = useMap();
  useEffect(() => {
    map.setView(MAURITIUS_CENTER, DEFAULT_ZOOM);
  }, [map]);
  return null;
}

function metricLabel(metric) {
  return (
    {
      download: "Download (Mbps)",
      upload: "Upload (Mbps)",
      latency: "Latency (ms)",
      jitter: "Jitter (ms)",
      packet_loss: "Packet loss (%)",
      qos: "QoS score",
      fulfilment: "Package fulfilment (%)",
    }[metric] || metric
  );
}

function formatMetric(value, metric) {
  if (value == null) return "—";
  if (metric === "qos") return `${Math.round(value)}/100`;
  if (metric === "latency" || metric === "jitter") return `${Number(value).toFixed(1)} ms`;
  if (metric === "packet_loss" || metric === "fulfilment") return `${Number(value).toFixed(1)}%`;
  return `${Number(value).toFixed(1)} Mbps`;
}

/**
 * Interactive Mauritius district QoS map (Phase 5).
 */
export default function MauritiusQosMap({ geojson, metric = "qos" }) {
  const features = geojson?.features || [];

  const styleFor = useMemo(() => {
    return (feature) => {
      const props = feature?.properties || {};
      const hasData = (props.tests || 0) > 0;
      return {
        fillColor: hasData ? props.colour || "#64748b" : "#1e293b",
        weight: 1.2,
        opacity: 1,
        color: "rgba(226, 232, 240, 0.55)",
        fillOpacity: hasData ? 0.72 : 0.25,
      };
    };
  }, []);

  if (!features.length) {
    return <p className="admin-empty">District geometry is unavailable.</p>;
  }

  return (
    <div className="admin-map-shell">
      <MapContainer
        className="admin-map"
        center={MAURITIUS_CENTER}
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom
        attributionControl
      >
        <FitMauritius />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON
          key={`${metric}-${features.map((f) => f.properties?.tests).join("-")}-${features.map((f) => f.properties?.metric_value).join("-")}`}
          data={geojson}
          style={styleFor}
          onEachFeature={(feature, layer) => {
            const p = feature.properties || {};
            layer.bindTooltip(
              `<strong>${p.name || "District"}</strong><br/>` +
                `${metricLabel(metric)}: ${formatMetric(p.metric_value, metric)}<br/>` +
                `Download: ${formatMetric(p.avg_download_mbps, "download")}<br/>` +
                `Upload: ${formatMetric(p.avg_upload_mbps, "upload")}<br/>` +
                `Ping: ${formatMetric(p.avg_ping_ms, "latency")}<br/>` +
                `Jitter: ${formatMetric(p.avg_jitter_ms, "jitter")}<br/>` +
                `Loss: ${formatMetric(p.avg_packet_loss_pct, "packet_loss")}<br/>` +
                `QoS: ${formatMetric(p.avg_qos_score, "qos")}<br/>` +
                `Fulfilment: ${formatMetric(p.avg_fulfilment_pct, "fulfilment")}<br/>` +
                `Tests: ${p.tests || 0}` +
                (p.rating ? `<br/>Rating: ${p.rating}` : ""),
              { sticky: true, className: "admin-map-tooltip" }
            );
          }}
        />
      </MapContainer>
    </div>
  );
}

export { metricLabel, formatMetric };
