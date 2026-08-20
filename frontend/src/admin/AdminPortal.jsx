import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpFromLine,
  Download,
  Gauge,
  MapPinned,
  Radio,
  RefreshCw,
  Shield,
  Sparkles,
  Trophy,
  Wifi,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  downloadAdminReport,
  fetchAdminAi,
  fetchAdminBenchmarks,
  fetchAdminDashboard,
  fetchAdminHeatmap,
  fetchAdminQosMap,
  fetchAdminHistory,
  fetchAdminIspAnalytics,
  fetchAdminPackages,
  createAdminPackage,
  updateAdminPackage,
  deactivateAdminPackage,
  updateAdminBenchmarks,
} from "../api/client";
import GlassCard from "../components/ui/GlassCard";
import { SkeletonCards } from "../components/ui/LoadingPulse";
import PanelHeader from "../components/ui/PanelHeader";
import SoftButton from "../components/ui/SoftButton";
import { formatDateTime, formatNumber, ratingClass } from "../utils/format";
import { ADMIN_PALETTE, AdminBarChart, AdminLineChart, metricDataset } from "./AdminCharts";
import MauritiusQosMap, { formatMetric, metricLabel } from "./MauritiusQosMap";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "isp", label: "ISP Analytics" },
  { id: "packages", label: "Packages" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "history", label: "History" },
  { id: "map", label: "QoS Map" },
  { id: "ai", label: "AI Analysis" },
];

const MAP_METRICS = [
  { id: "download", label: "Download" },
  { id: "upload", label: "Upload" },
  { id: "latency", label: "Latency" },
  { id: "jitter", label: "Jitter" },
  { id: "packet_loss", label: "Packet Loss" },
  { id: "qos", label: "QoS Score" },
  { id: "fulfilment", label: "Package Fulfilment" },
];

const DOW_OPTIONS = [
  { value: "", label: "Any day" },
  { value: "0", label: "Monday" },
  { value: "1", label: "Tuesday" },
  { value: "2", label: "Wednesday" },
  { value: "3", label: "Thursday" },
  { value: "4", label: "Friday" },
  { value: "5", label: "Saturday" },
  { value: "6", label: "Sunday" },
];

const EMPTY_PACKAGE_FORM = {
  isp_name: "",
  package_name: "",
  advertised_download_mbps: 100,
  advertised_upload_mbps: 40,
  notes: "",
  active: true,
};

const DAY_OPTIONS = [
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 365, label: "12 months" },
];

function EmptyHint({ children }) {
  return <p className="admin-empty">{children}</p>;
}

function KpiCard({ label, value, unit, icon: Icon, accent = "primary", delay = 0 }) {
  return (
    <motion.article
      className={`metric-stat glass ui-card-hover accent-${accent} admin-kpi`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="metric-stat-top">
        <span className="metric-stat-icon" aria-hidden="true">
          <Icon size={18} strokeWidth={1.75} />
        </span>
      </div>
      <p className="metric-stat-label">{label}</p>
      <p className="metric-stat-value">
        {value ?? "—"}
        {unit ? <span>{unit}</span> : null}
      </p>
    </motion.article>
  );
}

/**
 * Dedicated NOC-style Administrator Analytics Portal.
 * Isolated from the consumer speed-test experience.
 */
export default function AdminPortal({ onBack }) {
  const [tab, setTab] = useState("overview");
  const [days, setDays] = useState(90);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reportBusy, setReportBusy] = useState(false);
  const [dashboard, setDashboard] = useState(null);
  const [ispData, setIspData] = useState(null);
  const [benchmarks, setBenchmarks] = useState(null);
  const [history, setHistory] = useState(null);
  const [granularity, setGranularity] = useState("daily");
  const [heatmap, setHeatmap] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapFilters, setMapFilters] = useState({
    metric: "qos",
    isp: "",
    package: "",
    region: "",
    days: 30,
    date_from: "",
    date_to: "",
    day_of_week: "",
    hour_from: "",
    hour_to: "",
  });
  const [ai, setAi] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [profileDraft, setProfileDraft] = useState(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [packages, setPackages] = useState([]);
  const [packageForm, setPackageForm] = useState(EMPTY_PACKAGE_FORM);
  const [editingPackageId, setEditingPackageId] = useState(null);
  const [savingPackage, setSavingPackage] = useState(false);

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, isp, bench, heat] = await Promise.all([
        fetchAdminDashboard(days),
        fetchAdminIspAnalytics(days),
        fetchAdminBenchmarks(days),
        fetchAdminHeatmap(days),
      ]);
      setDashboard(dash);
      setIspData(isp);
      setBenchmarks(bench);
      setProfileDraft(bench.profile);
      setHeatmap(heat);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [days]);

  const loadHistory = useCallback(async () => {
    try {
      const data = await fetchAdminHistory(granularity, days);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [granularity, days]);

  const loadPackages = useCallback(async () => {
    try {
      const data = await fetchAdminPackages(false);
      setPackages(data?.packages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (tab === "packages") loadPackages();
  }, [tab, loadPackages]);

  useEffect(() => {
    if (tab !== "map") return undefined;
    let cancelled = false;
    setMapLoading(true);
    const filters = { ...mapFilters };
    if (filters.date_from || filters.date_to) {
      delete filters.days;
    }
    fetchAdminQosMap(filters)
      .then((data) => {
        if (!cancelled) setMapData(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setMapLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, mapFilters]);

  useEffect(() => {
    if (tab !== "ai") return undefined;
    let cancelled = false;
    setAiLoading(true);
    fetchAdminAi(days)
      .then((data) => {
        if (!cancelled) setAi(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setAiLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, days]);

  const handleReport = async () => {
    setReportBusy(true);
    setError(null);
    try {
      await downloadAdminReport(days);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setReportBusy(false);
    }
  };

  const handleSaveProfile = async () => {
    if (!profileDraft) return;
    setSavingProfile(true);
    setError(null);
    try {
      const data = await updateAdminBenchmarks(profileDraft, days);
      setBenchmarks(data);
      setProfileDraft(data.profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSavePackage = async () => {
    setSavingPackage(true);
    setError(null);
    try {
      const payload = {
        ...packageForm,
        advertised_download_mbps: Number(packageForm.advertised_download_mbps),
        advertised_upload_mbps: Number(packageForm.advertised_upload_mbps),
      };
      if (editingPackageId) {
        await updateAdminPackage(editingPackageId, payload);
      } else {
        await createAdminPackage(payload);
      }
      setPackageForm(EMPTY_PACKAGE_FORM);
      setEditingPackageId(null);
      await loadPackages();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingPackage(false);
    }
  };

  const handleEditPackage = (pkg) => {
    setEditingPackageId(pkg.id);
    setPackageForm({
      isp_name: pkg.isp_name,
      package_name: pkg.package_name,
      advertised_download_mbps: pkg.advertised_download_mbps,
      advertised_upload_mbps: pkg.advertised_upload_mbps,
      notes: pkg.notes || "",
      active: pkg.active,
    });
  };

  const handleDeactivatePackage = async (packageId) => {
    setSavingPackage(true);
    setError(null);
    try {
      await deactivateAdminPackage(packageId);
      if (editingPackageId === packageId) {
        setEditingPackageId(null);
        setPackageForm(EMPTY_PACKAGE_FORM);
      }
      await loadPackages();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingPackage(false);
    }
  };

  const isps = ispData?.isps || dashboard?.leaderboard || [];
  const labels = isps.map((row) => row.isp);

  return (
    <motion.div
      className="sq-view admin-portal"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <GlassCard className="iq-panel admin-toolbar" hover={false} delay={0.02}>
        <PanelHeader
          title="Administrator Analytics Portal"
          subtitle="National broadband QoS intelligence from stored SmartQoS measurements"
          action={
            <div className="admin-toolbar-actions">
              <SoftButton variant="ghost" onClick={onBack}>
                Consumer view
              </SoftButton>
              <SoftButton variant="ghost" onClick={loadCore}>
                <RefreshCw size={15} />
                Refresh
              </SoftButton>
              <SoftButton onClick={handleReport} loading={reportBusy}>
                <Download size={15} />
                Generate QoS Report
              </SoftButton>
            </div>
          }
        />
        <div className="admin-filters">
          <label className="mon-field">
            <span>Window</span>
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
              {DAY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <div className="admin-tabs" role="tablist" aria-label="Admin sections">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={tab === item.id}
                className={`admin-tab ${tab === item.id ? "is-active" : ""}`}
                onClick={() => setTab(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        {error && (
          <p className="mon-error" role="alert">
            {error}
          </p>
        )}
      </GlassCard>

      {loading ? (
        <SkeletonCards count={4} />
      ) : (
        <AnimatePresence mode="wait">
          {tab === "overview" && (
            <OverviewSection key="overview" dashboard={dashboard} />
          )}
          {tab === "isp" && (
            <IspSection key="isp" isps={isps} labels={labels} />
          )}
          {tab === "packages" && (
            <PackagesSection
              key="packages"
              packages={packages}
              form={packageForm}
              setForm={setPackageForm}
              editingId={editingPackageId}
              onSave={handleSavePackage}
              onEdit={handleEditPackage}
              onDeactivate={handleDeactivatePackage}
              onCancelEdit={() => {
                setEditingPackageId(null);
                setPackageForm(EMPTY_PACKAGE_FORM);
              }}
              saving={savingPackage}
            />
          )}
          {tab === "benchmarks" && (
            <BenchmarkSection
              key="benchmarks"
              benchmarks={benchmarks}
              profileDraft={profileDraft}
              setProfileDraft={setProfileDraft}
              onSave={handleSaveProfile}
              saving={savingProfile}
            />
          )}
          {tab === "history" && (
            <HistorySection
              key="history"
              history={history}
              granularity={granularity}
              setGranularity={setGranularity}
            />
          )}
          {tab === "map" && (
            <MapSection
              key="map"
              mapData={mapData}
              loading={mapLoading}
              filters={mapFilters}
              setFilters={setMapFilters}
              heatmap={heatmap}
            />
          )}
          {tab === "ai" && <AiSection key="ai" ai={ai} loading={aiLoading} />}
        </AnimatePresence>
      )}
    </motion.div>
  );
}

function OverviewSection({ dashboard }) {
  const kpis = dashboard?.kpis;
  const live = dashboard?.live;
  const leaderboard = dashboard?.leaderboard || [];
  const overview = dashboard?.qos_overview || [];

  return (
    <motion.div
      className="admin-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <div className="admin-kpi-grid">
        <KpiCard label="Total tests" value={kpis?.total_tests ?? 0} icon={Activity} accent="download" delay={0.04} />
        <KpiCard label="ISPs observed" value={kpis?.isp_count ?? 0} icon={Wifi} accent="upload" delay={0.06} />
        <KpiCard
          label="Mean QoS"
          value={kpis?.avg_qos_score != null ? formatNumber(kpis.avg_qos_score, 0) : "—"}
          unit="/100"
          icon={Gauge}
          accent="primary"
          delay={0.08}
        />
        <KpiCard
          label="Avg download"
          value={kpis?.avg_download_mbps != null ? formatNumber(kpis.avg_download_mbps, 1) : "—"}
          unit="Mbps"
          icon={ArrowDownToLine}
          accent="download"
          delay={0.1}
        />
        <KpiCard
          label="Avg ping"
          value={kpis?.avg_ping_ms != null ? formatNumber(kpis.avg_ping_ms, 0) : "—"}
          unit="ms"
          icon={Zap}
          accent="ping"
          delay={0.12}
        />
        <KpiCard
          label="Tests (24h)"
          value={kpis?.tests_24h ?? 0}
          icon={Radio}
          accent="jitter"
          delay={0.14}
        />
      </div>

      <div className="admin-split">
        <GlassCard className="iq-panel" delay={0.08}>
          <PanelHeader
            title="Live statistics"
            subtitle="Latest stored sample and monitoring heartbeat"
            action={<Shield size={18} color="var(--muted)" />}
          />
          <div className="admin-live-grid">
            <div>
              <span>Monitoring</span>
              <strong className={live?.monitoring_enabled ? "on" : "off"}>
                {live?.monitoring_running
                  ? "Measuring"
                  : live?.monitoring_enabled
                    ? "Armed"
                    : "Idle"}
              </strong>
            </div>
            <div>
              <span>Last ISP</span>
              <strong>{live?.last_isp || "—"}</strong>
            </div>
            <div>
              <span>Last region</span>
              <strong>{live?.last_region || "—"}</strong>
            </div>
            <div>
              <span>Last score</span>
              <strong className={ratingClass(live?.last_rating)}>
                {live?.last_score != null ? `${live.last_score}/100` : "—"}
              </strong>
            </div>
            <div>
              <span>Last test</span>
              <strong>{kpis?.last_test_at ? formatDateTime(kpis.last_test_at) : "—"}</strong>
            </div>
            <div>
              <span>Excellent share</span>
              <strong>
                {kpis?.excellent_pct != null ? `${formatNumber(kpis.excellent_pct, 1)}%` : "—"}
              </strong>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="iq-panel" delay={0.1}>
          <PanelHeader title="QoS overview" subtitle="Rating distribution across the selected window" />
          {overview.length === 0 ? (
            <EmptyHint>No QoS ratings stored yet.</EmptyHint>
          ) : (
            <div className="admin-qos-bars">
              {overview.map((bucket) => (
                <div key={bucket.rating} className="admin-qos-row">
                  <span className={`iq-pill ${ratingClass(bucket.rating)}`}>{bucket.rating}</span>
                  <div className="admin-qos-track" aria-hidden="true">
                    <span
                      className={`admin-qos-fill ${ratingClass(bucket.rating)}`}
                      style={{ width: `${Math.max(bucket.pct, bucket.count ? 4 : 0)}%` }}
                    />
                  </div>
                  <strong>
                    {bucket.count} · {formatNumber(bucket.pct, 1)}%
                  </strong>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard className="iq-panel" delay={0.12}>
        <PanelHeader
          title="ISP leaderboard"
          subtitle="Ranked by mean QoS score from speed_tests"
          action={<Trophy size={18} color="var(--muted)" />}
        />
        {leaderboard.length === 0 ? (
          <EmptyHint>No ISP samples yet. Run consumer tests to populate the leaderboard.</EmptyHint>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>ISP</th>
                  <th>Tests</th>
                  <th>QoS</th>
                  <th>Download</th>
                  <th>Upload</th>
                  <th>Ping</th>
                  <th>Jitter</th>
                  <th>Loss</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((row) => (
                  <tr key={row.isp}>
                    <td>{row.rank}</td>
                    <td>{row.isp}</td>
                    <td>{row.tests}</td>
                    <td className={ratingClass(row.latest_rating)}>
                      {row.avg_qos_score != null ? formatNumber(row.avg_qos_score, 0) : "—"}
                    </td>
                    <td>{formatNumber(row.avg_download_mbps, 1)}</td>
                    <td>{formatNumber(row.avg_upload_mbps, 1)}</td>
                    <td>{formatNumber(row.avg_ping_ms, 0)}</td>
                    <td>{formatNumber(row.avg_jitter_ms, 1)}</td>
                    <td>{formatNumber(row.avg_packet_loss_pct, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </motion.div>
  );
}

function PackagesSection({
  packages,
  form,
  setForm,
  editingId,
  onSave,
  onEdit,
  onDeactivate,
  onCancelEdit,
  saving,
}) {
  const onField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <motion.div
      className="admin-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <GlassCard className="iq-panel" delay={0.04}>
        <PanelHeader
          title={editingId ? "Edit internet package" : "Add internet package"}
          subtitle="Administrator-configured advertised speeds — nothing commercial is hard-coded"
        />
        <div className="admin-profile-grid">
          <label className="mon-field">
            <span>ISP</span>
            <input
              type="text"
              value={form.isp_name}
              placeholder="e.g. Emtel"
              onChange={(e) => onField("isp_name", e.target.value)}
            />
          </label>
          <label className="mon-field">
            <span>Package</span>
            <input
              type="text"
              value={form.package_name}
              placeholder="e.g. 100 Mbps"
              onChange={(e) => onField("package_name", e.target.value)}
            />
          </label>
          <label className="mon-field">
            <span>Advertised download (Mbps)</span>
            <input
              type="number"
              step="0.1"
              min="0.1"
              value={form.advertised_download_mbps}
              onChange={(e) => onField("advertised_download_mbps", e.target.value)}
            />
          </label>
          <label className="mon-field">
            <span>Advertised upload (Mbps)</span>
            <input
              type="number"
              step="0.1"
              min="0.1"
              value={form.advertised_upload_mbps}
              onChange={(e) => onField("advertised_upload_mbps", e.target.value)}
            />
          </label>
          <label className="mon-field" style={{ gridColumn: "1 / -1" }}>
            <span>Notes</span>
            <input
              type="text"
              value={form.notes}
              placeholder="Optional"
              onChange={(e) => onField("notes", e.target.value)}
            />
          </label>
          <div className="mon-actions">
            <SoftButton onClick={onSave} loading={saving} disabled={!form.isp_name || !form.package_name}>
              {editingId ? "Update package" : "Add package"}
            </SoftButton>
            {editingId ? (
              <SoftButton variant="ghost" onClick={onCancelEdit}>
                Cancel
              </SoftButton>
            ) : null}
          </div>
        </div>
      </GlassCard>

      <GlassCard className="iq-panel" delay={0.08}>
        <PanelHeader
          title="Configured packages"
          subtitle="Used for download/upload fulfilment % when selected on a test"
        />
        {packages.length === 0 ? (
          <EmptyHint>
            No packages yet. Add ISP plans here so measurements can report fulfilment against
            advertised speeds.
          </EmptyHint>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ISP</th>
                  <th>Package</th>
                  <th>↓ Mbps</th>
                  <th>↑ Mbps</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {packages.map((pkg) => (
                  <tr key={pkg.id}>
                    <td>{pkg.isp_name}</td>
                    <td>{pkg.package_name}</td>
                    <td>{formatNumber(pkg.advertised_download_mbps, 1)}</td>
                    <td>{formatNumber(pkg.advertised_upload_mbps, 1)}</td>
                    <td>{pkg.active ? "Active" : "Inactive"}</td>
                    <td>
                      <div className="admin-toolbar-actions">
                        <SoftButton variant="ghost" onClick={() => onEdit(pkg)}>
                          Edit
                        </SoftButton>
                        {pkg.active ? (
                          <SoftButton variant="ghost" onClick={() => onDeactivate(pkg.id)}>
                            Deactivate
                          </SoftButton>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </motion.div>
  );
}

function IspSection({ isps, labels }) {
  if (!isps.length) {
    return (
      <GlassCard className="iq-panel">
        <EmptyHint>No ISP comparison data in this window.</EmptyHint>
      </GlassCard>
    );
  }

  const charts = [
    { title: "Download comparison", unit: "Mbps", key: "avg_download_mbps", color: "#3b82f6" },
    { title: "Upload comparison", unit: "Mbps", key: "avg_upload_mbps", color: "#22c55e" },
    { title: "Ping comparison", unit: "ms", key: "avg_ping_ms", color: "#f59e0b" },
    { title: "Jitter comparison", unit: "ms", key: "avg_jitter_ms", color: "#a78bfa" },
    { title: "Packet loss comparison", unit: "%", key: "avg_packet_loss_pct", color: "#f43f5e" },
    { title: "QoS score comparison", unit: "/100", key: "avg_qos_score", color: "#06b6d4" },
  ];

  return (
    <motion.div
      className="admin-chart-grid"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      {charts.map((chart, index) => (
        <GlassCard key={chart.key} className="iq-panel admin-chart-card" delay={0.04 + index * 0.03}>
          <PanelHeader title={chart.title} subtitle={`Mean ${chart.unit} by ISP`} />
          <div className="admin-chart">
            <AdminBarChart
              labels={labels}
              yTitle={chart.unit}
              datasets={[
                metricDataset(
                  chart.title,
                  isps.map((row) => row[chart.key]),
                  chart.color
                ),
              ]}
            />
          </div>
        </GlassCard>
      ))}
    </motion.div>
  );
}

function BenchmarkSection({ benchmarks, profileDraft, setProfileDraft, onSave, saving }) {
  const rankings = benchmarks?.rankings || [];
  const labels = rankings.map((row) => row.isp);

  const onField = (key, value) => {
    setProfileDraft((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <motion.div
      className="admin-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <GlassCard className="iq-panel" delay={0.04}>
        <PanelHeader
          title="Ideal Broadband Profile"
          subtitle="Configurable thresholds used to score every ISP"
        />
        {profileDraft && (
          <div className="admin-profile-grid">
            {[
              ["download_mbps", "Download (Mbps)"],
              ["upload_mbps", "Upload (Mbps)"],
              ["ping_ms", "Ping (ms)"],
              ["jitter_ms", "Jitter (ms)"],
              ["packet_loss_pct", "Loss (%)"],
              ["overall_score", "QoS score"],
            ].map(([key, label]) => (
              <label key={key} className="mon-field">
                <span>{label}</span>
                <input
                  type="number"
                  step="0.1"
                  value={profileDraft[key]}
                  onChange={(e) => onField(key, Number(e.target.value))}
                />
              </label>
            ))}
            <div className="mon-actions">
              <SoftButton onClick={onSave} loading={saving}>
                Save thresholds
              </SoftButton>
            </div>
          </div>
        )}
      </GlassCard>

      <GlassCard className="iq-panel" delay={0.08}>
        <PanelHeader title="Benchmark compliance" subtitle="Share of samples meeting each ideal target" />
        {rankings.length === 0 ? (
          <EmptyHint>No ISP samples to benchmark.</EmptyHint>
        ) : (
          <div className="admin-chart admin-chart-wide">
            <AdminBarChart
              labels={labels}
              yTitle="% meeting target"
              datasets={["Download", "Upload", "Ping", "Jitter", "Packet Loss", "QoS Score"].map(
                (metric, index) =>
                  metricDataset(
                    metric,
                    rankings.map((row) => {
                      const found = row.metrics.find((m) => m.metric === metric);
                      return found?.compliance_pct ?? null;
                    }),
                    ADMIN_PALETTE[index]
                  )
              )}
            />
          </div>
        )}
      </GlassCard>

      {rankings.map((row) => (
        <GlassCard key={row.isp} className="iq-panel compact" delay={0.1}>
          <PanelHeader
            title={row.isp}
            subtitle={`Composite compliance ${row.composite_score != null ? `${row.composite_score}%` : "—"} · ${row.tests} tests`}
          />
          <div className="mon-last-grid">
            {row.metrics.map((metric) => (
              <div key={metric.metric}>
                <span>{metric.metric}</span>
                <strong className={metric.meets_target ? "on" : "off"}>
                  {formatNumber(metric.actual, metric.unit === "%" ? 2 : 1)} {metric.unit}
                  {" · "}
                  {metric.compliance_pct != null ? `${formatNumber(metric.compliance_pct, 0)}%` : "—"}
                </strong>
              </div>
            ))}
          </div>
        </GlassCard>
      ))}
    </motion.div>
  );
}

function HistorySection({ history, granularity, setGranularity }) {
  const points = history?.points || [];
  const labels = points.map((p) => p.period);

  return (
    <motion.div
      className="admin-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <GlassCard className="iq-panel" hover={false}>
        <PanelHeader
          title="Historical analytics"
          subtitle="Daily, weekly and monthly averages from stored tests"
          action={
            <div className="admin-tabs compact">
              {["daily", "weekly", "monthly"].map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`admin-tab ${granularity === item ? "is-active" : ""}`}
                  onClick={() => setGranularity(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          }
        />
        {points.length === 0 ? (
          <EmptyHint>No historical points in this window.</EmptyHint>
        ) : (
          <>
            <div className="admin-chart admin-chart-wide">
              <AdminLineChart
                labels={labels}
                yTitle="Mbps / score"
                datasets={[
                  metricDataset(
                    "Download",
                    points.map((p) => p.avg_download_mbps),
                    "#3b82f6",
                    { fill: true, line: true }
                  ),
                  metricDataset(
                    "Upload",
                    points.map((p) => p.avg_upload_mbps),
                    "#22c55e",
                    { line: true }
                  ),
                  metricDataset(
                    "QoS score",
                    points.map((p) => p.avg_qos_score),
                    "#06b6d4",
                    { line: true }
                  ),
                ]}
              />
            </div>
            <div className="admin-chart admin-chart-wide" style={{ marginTop: 16 }}>
              <AdminLineChart
                labels={labels}
                yTitle="ms / %"
                datasets={[
                  metricDataset(
                    "Ping",
                    points.map((p) => p.avg_ping_ms),
                    "#f59e0b",
                    { line: true }
                  ),
                  metricDataset(
                    "Jitter",
                    points.map((p) => p.avg_jitter_ms),
                    "#a78bfa",
                    { line: true }
                  ),
                  metricDataset(
                    "Packet loss",
                    points.map((p) => p.avg_packet_loss_pct),
                    "#f43f5e",
                    { line: true }
                  ),
                ]}
              />
            </div>
          </>
        )}
      </GlassCard>
    </motion.div>
  );
}

function MapSection({ mapData, loading, filters, setFilters, heatmap }) {
  const meta = mapData?.meta || {};
  const legend = mapData?.legend;
  const features = mapData?.features || [];
  const onFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <motion.div
      className="admin-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <GlassCard className="iq-panel" delay={0.04}>
        <PanelHeader
          title="Mauritius geographic QoS map"
          subtitle="District averages with live filters — colour = Excellent→Critical scale"
          action={<MapPinned size={18} color="var(--muted)" />}
        />

        <div className="admin-map-modes" role="tablist" aria-label="Map metric">
          {MAP_METRICS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`admin-tab ${filters.metric === item.id ? "is-active" : ""}`}
              onClick={() => onFilter("metric", item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="admin-map-filters">
          <label className="mon-field">
            <span>ISP</span>
            <select value={filters.isp} onChange={(e) => onFilter("isp", e.target.value)}>
              <option value="">All ISPs</option>
              {(meta.available_isps || []).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="mon-field">
            <span>Package</span>
            <select
              value={filters.package}
              onChange={(e) => onFilter("package", e.target.value)}
            >
              <option value="">All packages</option>
              {(meta.available_packages || []).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="mon-field">
            <span>Region</span>
            <select
              value={filters.region}
              onChange={(e) => onFilter("region", e.target.value)}
            >
              <option value="">All districts</option>
              {(meta.available_regions || []).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label className="mon-field">
            <span>Date window</span>
            <select
              value={filters.days}
              onChange={(e) =>
                onFilter("days", Number(e.target.value))
              }
              disabled={Boolean(filters.date_from || filters.date_to)}
            >
              {DAY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="mon-field">
            <span>From date</span>
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => onFilter("date_from", e.target.value)}
            />
          </label>
          <label className="mon-field">
            <span>To date</span>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => onFilter("date_to", e.target.value)}
            />
          </label>
          <label className="mon-field">
            <span>Day of week</span>
            <select
              value={filters.day_of_week}
              onChange={(e) => onFilter("day_of_week", e.target.value)}
            >
              {DOW_OPTIONS.map((opt) => (
                <option key={opt.label} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="mon-field">
            <span>Hour from (UTC)</span>
            <input
              type="number"
              min="0"
              max="23"
              placeholder="e.g. 18"
              value={filters.hour_from}
              onChange={(e) => onFilter("hour_from", e.target.value)}
            />
          </label>
          <label className="mon-field">
            <span>Hour to (UTC)</span>
            <input
              type="number"
              min="0"
              max="23"
              placeholder="e.g. 21"
              value={filters.hour_to}
              onChange={(e) => onFilter("hour_to", e.target.value)}
            />
          </label>
        </div>

        <p className="admin-map-meta">
          Showing <strong>{metricLabel(filters.metric)}</strong> ·{" "}
          {meta.total_tests ?? 0} tests · {meta.districts_with_data ?? 0} districts with data
          {filters.hour_from !== "" || filters.hour_to !== ""
            ? ` · time ${filters.hour_from || "00"}:00–${filters.hour_to || "23"}:00 UTC`
            : ""}
        </p>

        {loading ? (
          <SkeletonCards count={1} />
        ) : (
          <MauritiusQosMap geojson={mapData} metric={filters.metric} />
        )}

        {legend ? (
          <div className="admin-map-legend">
            <h4>Colour scale</h4>
            <p>{legend.note}</p>
            <div className="admin-map-legend-row">
              {(legend.bands || []).map((band) => (
                <div key={band.rating} className="admin-map-legend-item">
                  <span style={{ background: band.colour }} aria-hidden="true" />
                  <div>
                    <strong className={ratingClass(band.rating)}>{band.rating}</strong>
                    <small>{band.meaning}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </GlassCard>

      <GlassCard className="iq-panel" delay={0.08}>
        <PanelHeader title="District summary" subtitle="All metrics for the active filter set" />
        {features.length === 0 ? (
          <EmptyHint>No map features returned.</EmptyHint>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>District</th>
                  <th>Tests</th>
                  <th>Download</th>
                  <th>Upload</th>
                  <th>Ping</th>
                  <th>Jitter</th>
                  <th>Loss</th>
                  <th>QoS</th>
                  <th>Fulfilment</th>
                </tr>
              </thead>
              <tbody>
                {features.map((feature) => {
                  const p = feature.properties || {};
                  return (
                    <tr key={p.id || p.name}>
                      <td>
                        <span
                          className="admin-map-swatch"
                          style={{ background: p.colour || "#334155" }}
                        />
                        {p.name}
                      </td>
                      <td>{p.tests || 0}</td>
                      <td>{formatMetric(p.avg_download_mbps, "download")}</td>
                      <td>{formatMetric(p.avg_upload_mbps, "upload")}</td>
                      <td>{formatMetric(p.avg_ping_ms, "latency")}</td>
                      <td>{formatMetric(p.avg_jitter_ms, "jitter")}</td>
                      <td>{formatMetric(p.avg_packet_loss_pct, "packet_loss")}</td>
                      <td className={ratingClass(p.rating)}>
                        {formatMetric(p.avg_qos_score, "qos")}
                      </td>
                      <td>{formatMetric(p.avg_fulfilment_pct, "fulfilment")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      {heatmap?.cells?.length ? (
        <GlassCard className="iq-panel" delay={0.1}>
          <PanelHeader
            title="Locality cards (legacy)"
            subtitle="Server-label heatmap retained for report continuity"
          />
          <div className="admin-heat-grid">
            {heatmap.cells.map((cell) => (
              <article
                key={cell.region}
                className={`admin-heat-cell ${cell.tests ? "has-data" : "is-empty"}`}
              >
                <h3>{cell.region}</h3>
                <p className={`admin-heat-score ${ratingClass(cell.rating)}`}>
                  {cell.avg_qos_score != null ? formatNumber(cell.avg_qos_score, 0) : "—"}
                </p>
                <p>
                  {cell.tests} tests · {formatNumber(cell.avg_download_mbps, 1)} Mbps ·{" "}
                  {formatNumber(cell.avg_ping_ms, 0)} ms
                </p>
              </article>
            ))}
          </div>
        </GlassCard>
      ) : null}
    </motion.div>
  );
}

function AiSection({ ai, loading }) {
  if (loading) {
    return <SkeletonCards count={3} />;
  }
  if (!ai) {
    return (
      <GlassCard className="iq-panel">
        <EmptyHint>AI analysis is unavailable.</EmptyHint>
      </GlassCard>
    );
  }
  return (
    <motion.div
      className="admin-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
    >
      <GlassCard className="iq-panel" delay={0.04}>
        <PanelHeader
          title="Market summary"
          subtitle={`Provider · ${ai.model_provider}`}
          action={<Sparkles size={18} color="var(--accent)" />}
        />
        <p className="admin-copy">{ai.market_summary}</p>
        {ai.recommendations?.length > 0 && (
          <ul className="admin-rec-list">
            {ai.recommendations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </GlassCard>
      {(ai.isps || []).map((card, index) => (
        <GlassCard key={card.isp} className="iq-panel compact" delay={0.06 + index * 0.03}>
          <PanelHeader
            title={card.isp}
            subtitle={`${card.tests} tests · ${card.rating || "Unrated"}`}
          />
          <p className="admin-copy">{card.summary}</p>
          <div className="admin-split tight">
            <div>
              <h4>Strengths</h4>
              <ul>{(card.strengths || []).map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h4>Gaps</h4>
              <ul>{(card.weaknesses || []).map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          <h4>Recommendations</h4>
          <ul className="admin-rec-list">
            {(card.recommendations || []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </GlassCard>
      ))}
    </motion.div>
  );
}
