import { useState } from "react";
import { Server, Edit3, Download, Sun, Upload } from "lucide-react";

/* ── local data ── */
const SITES_SYNC = [
  { name: "Duliajan",           role: "hub", status: "connected", lastSync: "2 min ago",  dot: "#16a34a" },
  { name: "Moran",              role: "",    status: "connected", lastSync: "4 min ago",  dot: "#16a34a" },
  { name: "Naharkatiya",        role: "",    status: "connected", lastSync: "6 min ago",  dot: "#16a34a" },
  { name: "KG Basin",           role: "",    status: "pending",   lastSync: "18 min ago", dot: "#d97706" },
  { name: "Jorhat",             role: "",    status: "connected", lastSync: "7 min ago",  dot: "#16a34a" },
  { name: "Baghjan",            role: "",    status: "connected", lastSync: "11 min ago", dot: "#16a34a" },
  { name: "Rajasthan (Jodhpur)",role: "",    status: "pending",   lastSync: "34 min ago", dot: "#d97706" },
];

const THRESHOLD_INIT = [
  { category: "Dropped object",              threshold: "40",  source: "DROPS calculator v3",        lastEdited: "12 Aug 2026" },
  { category: "Fall from height",            threshold: "300", source: "Energy-threshold policy v4", lastEdited: "12 Aug 2026" },
  { category: "Mobile equipment / motion",   threshold: "1200",source: "Vehicle impact model",       lastEdited: "01 Sep 2026" },
  { category: "Pressure release",            threshold: "500", source: "Process safety review",      lastEdited: "02 Sep 2026" },
  { category: "Electrical",                  threshold: "50",  source: "IEC 60479-1",               lastEdited: "12 Aug 2026" },
  { category: "Thermal / fire contact",      threshold: "80",  source: "SFPE handbook",             lastEdited: "12 Aug 2026" },
  { category: "Toxic / asphyxiant",          threshold: "–",   source: "IDLH table",               lastEdited: "12 Aug 2026" },
];

const YAML_TEXT = `sites:
  duliajan:
    default_height_m: 2.0
    default_mass_kg: 25
    default_pressure_kPa: 700
    energy_model: drops_v3
  baghjan:
    default_height_m: 3.5
    default_mass_kg: 40
    default_pressure_kPa: 1100
    energy_model: drops_v3
  kg_basin:
    default_height_m: 4.0
    default_mass_kg: 60
    default_pressure_kPa: 2200
    energy_model: process_v2
  moran:
    default_height_m: 2.5
    default_mass_kg: 30
    default_pressure_kPa: 850
    energy_model: drops_v3
  jorhat:
    default_height_m: 2.0
    default_mass_kg: 20
    default_pressure_kPa: 600
    energy_model: drops_v3`;

const EVAL_ROWS = [
  { label: "Recall · P-SIF",           v: 0.94, color: "#16a34a", note: ""                                   },
  { label: "Recall · H-SIF",           v: 0.91, color: "#16a34a", note: ""                                   },
  { label: "Recall · Exposure",        v: 0.88, color: "#16a34a", note: ""                                   },
  { label: "Span F1 · energy source",  v: 0.86, color: "#16a34a", note: ""                                   },
  { label: "Span F1 · release",        v: 0.83, color: "#d97706", note: ""                                   },
  { label: "Span F1 · person in path", v: 0.79, color: "#d97706", note: ""                                   },
  { label: "Span F1 · control",        v: 0.71, color: "#dc2626", note: "weakest — drives most overrides"    },
  { label: "Human override rate 30d",  v: 0.084, color: "#d97706", pct: true, note: ""                       },
];

/* ── mini select ── */
function Sel({ label, opts }: { label: string; opts: string[] }) {
  return (
    <select className="border border-slate-200 bg-white rounded-md px-2.5 py-1.5 text-[12px] text-slate-700 focus:outline-none cursor-pointer" style={{ minWidth: 110 }}>
      <option>{label}</option>
      {opts.map((o) => <option key={o}>{o}</option>)}
    </select>
  );
}

/* ═══════════════════════════ SYSTEM PAGE ═══════════════════════════ */
export default function SystemPage() {
  const [thresholds, setThresholds] = useState(THRESHOLD_INIT.map((t) => t.threshold));

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>

      {/* ── Filter / status bar ── */}
      <header className="flex items-center gap-3 px-5 py-2.5 bg-white border-b border-slate-200 flex-wrap shrink-0">
        <Sel label="This week"          opts={["Last week","Last 30 days","Last 90 days"]} />
        <Sel label="Site 7"             opts={["Duliajan","Moran","Baghjan","KG Basin"]} />
        <Sel label="Activity: All"      opts={["Lifting","Confined Space","Hot Work","Driving"]} />
        <Sel label="Rule: All"          opts={["LF","EI","CS","WH","HW"]} />
        <Sel label="Verdict: All"       opts={["P-SIF","Exposure","Insufficient","Non-Event"]} />
        <Sel label="Review: Unreviewed" opts={["All","Reviewed","Needs Info","Pending"]} />

        <div className="ml-auto flex items-center gap-4 text-[12px] text-slate-500 flex-wrap">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold"
            style={{ background: "#fdf1e9", color: "#a15c1f", border: "1px solid #f3d8bc" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> Offline · 06:40 · 3 pending
          </span>
          <button className="flex items-center gap-1 hover:text-slate-700">
            <Sun className="w-3.5 h-3.5" /> Light
          </button>
          <span className="text-slate-400">Field</span>
          <button className="flex items-center gap-1 hover:text-slate-700">
            <Upload className="w-3.5 h-3.5" /> Export
          </button>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> State: Live
          </span>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
              style={{ background: "#2f5fb3" }}>SB</div>
            <span className="font-medium text-slate-700">S. Borgohain</span>
          </div>
        </div>
      </header>

      <div className="max-w-[1500px] mx-auto px-5 py-4 space-y-4">

        {/* ── Models card ── */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-3">
            <Server className="w-4 h-4 text-slate-400 shrink-0" />
            <h2 className="font-bold text-slate-800 text-sm">Models</h2>
            <span className="text-[11px] text-slate-400">run mode CPU, fully offline · 16 GB RAM host</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12.5px]" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
                  {["Component","Model","Role","Version","Size","Quantisation","Latency"].map((h, i) => (
                    <th key={h} className={`py-2.5 px-4 text-left font-bold ${i >= 4 ? "text-right" : ""}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { component: "Rule engine",     model: "policy_table_v4.yaml", role: "Deterministic triage",   version: "4.2",   size: "0.4 MB", quant: "—",    latency: "< 1 ms" },
                  { component: "Fast classifier", model: "muril-base-cased",     role: "SIF / Exposure label",   version: "1.0.0", size: "471 MB", quant: "INT8", latency: "42 ms"  },
                  { component: "Extractor",       model: "xlm-r-token-tagger",   role: "Energy span extraction", version: "2.3.1", size: "1.1 GB", quant: "INT8", latency: "118 ms" },
                  { component: "Reader",          model: "qwen2.5-3b-instruct",  role: "Uncertain-lane detail",  version: "2.5.0", size: "3.1 GB", quant: "Q4_K", latency: "2.4 s"  },
                  { component: "Language ID",     model: "fasttext-lid-176",     role: "Language detection",     version: "0.9.2", size: "0.9 MB", quant: "—",    latency: "< 1 ms" },
                ].map((row) => (
                  <tr key={row.component} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-800">{row.component}</td>
                    <td className="px-4 py-3 font-mono text-[11.5px] text-slate-600">{row.model}</td>
                    <td className="px-4 py-3 text-slate-500">{row.role}</td>
                    <td className="px-4 py-3 font-mono text-[11.5px] text-slate-500">{row.version}</td>
                    <td className="px-4 py-3 font-mono text-right text-slate-600">{row.size}</td>
                    <td className="px-4 py-3 text-right text-slate-500">{row.quant}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-right" style={{ color: "#0d5555" }}>{row.latency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Thresholds + YAML ── */}
        <div className="grid grid-cols-2 gap-4">
          {/* Editable thresholds */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
              <Edit3 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <h2 className="font-bold text-slate-800 text-sm">Energy thresholds</h2>
              <span className="text-[11px] text-slate-400 ml-1">— editable</span>
            </div>
            <table className="w-full text-[12.5px]" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
                  <th className="py-2.5 px-4 text-left font-bold">Category</th>
                  <th className="py-2.5 px-4 text-center font-bold">Threshold (J)</th>
                  <th className="py-2.5 px-4 text-left font-bold">Source</th>
                  <th className="py-2.5 px-4 text-left font-bold">Last edited</th>
                </tr>
              </thead>
              <tbody>
                {THRESHOLD_INIT.map((row, i) => (
                  <tr key={row.category} className="border-b border-slate-50 last:border-0">
                    <td className="px-4 py-2.5 font-medium text-slate-700">{row.category}</td>
                    <td className="px-4 py-2.5 text-center">
                      <input
                        value={thresholds[i]}
                        onChange={(e) => setThresholds((prev) => { const n = [...prev]; n[i] = e.target.value; return n; })}
                        className="w-20 text-center font-mono text-[12px] border border-slate-200 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-cyan-300 transition-shadow"
                        style={{ color: "#0d5555" }}
                      />
                    </td>
                    <td className="px-4 py-2.5 text-slate-400 text-[11px]">{row.source}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-400 text-[11px]">{row.lastEdited}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* YAML block */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between shrink-0">
              <h2 className="font-bold text-slate-800 text-sm font-mono">site_defaults.yaml</h2>
              <span className="text-[10px] text-slate-400">per-site energy defaults</span>
            </div>
            <pre className="flex-1 px-5 py-4 text-[11.5px] font-mono leading-relaxed overflow-auto m-0"
              style={{ background: "#f8fafb", color: "#334155" }}>
              {YAML_TEXT}
            </pre>
          </div>
        </div>

        {/* ── Coverage controls ── */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <h2 className="font-bold text-slate-800 text-sm mb-4">Coverage controls</h2>
          <div className="grid grid-cols-3 gap-x-12 gap-y-0">
            {[
              ["Review error rate α",   "0.10"],
              ["Coverage guarantee",    "90.4%"],
              ["Uncertain-lane size",   "481 · 14.8%"],
              ["Calibration set",       "1,200 reports"],
              ["Last recalibration",    "02 Sep 2026"],
              ["Override rate 30d",     "8.4%"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-2.5 border-b border-slate-50">
                <span className="text-[12.5px] text-slate-500">{k}</span>
                <span className="font-mono font-bold text-[13px] text-slate-800">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Sync topology + Last evaluation ── */}
        <div className="grid grid-cols-2 gap-4">
          {/* Sync topology */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
            <h2 className="font-bold text-slate-800 text-sm mb-0.5">Sync topology</h2>
            <p className="text-[11px] text-slate-400 mb-4">hub: central Postgres, Duliajan</p>
            <div className="space-y-1.5">
              {SITES_SYNC.map((s) => (
                <div key={s.name}
                  className={`flex items-center gap-3 py-2 px-3 rounded-lg ${s.role === "hub" ? "bg-slate-50 border border-slate-200" : ""}`}>
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: s.dot }} />
                  <span className={`flex-1 text-[13px] ${s.role === "hub" ? "font-bold text-slate-800" : "font-medium text-slate-600"}`}>
                    {s.name}
                    {s.role === "hub" && (
                      <span className="ml-2 text-[9px] font-bold uppercase tracking-widest text-slate-400">HUB</span>
                    )}
                  </span>
                  <span className="font-mono text-[11px] text-slate-400 shrink-0">{s.lastSync}</span>
                  <span className="text-[11px] font-semibold w-20 text-right shrink-0" style={{ color: s.dot }}>{s.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Last evaluation */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
            <h2 className="font-bold text-slate-800 text-sm mb-0.5">Last evaluation</h2>
            <p className="text-[11px] text-slate-400 mb-4">02 Sep 2026 · 1,842 held-out reports</p>
            <div className="space-y-3">
              {EVAL_ROWS.map((row) => {
                const display = row.pct
                  ? `${(row.v * 100).toFixed(1)}%`
                  : row.v.toFixed(2);
                const barW = row.pct ? row.v * 100 : row.v * 100;
                return (
                  <div key={row.label}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[12px] text-slate-500">{row.label}</span>
                      <span className="font-mono font-bold text-[12px] text-slate-800">{display}</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#f0f2f5" }}>
                      <div className="h-full rounded-full transition-all" style={{ width: `${barW}%`, background: row.color }} />
                    </div>
                    {row.note && (
                      <div className="text-[10px] text-slate-400 mt-0.5 italic">{row.note}</div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400 italic leading-relaxed">
              Honest numbers. Span F1 on control is the weakest link and drives most overrides.
            </div>
          </div>
        </div>

        {/* ── Weekly brief ── */}
        <div className="flex justify-end pb-2">
          <button className="flex items-center gap-2 text-[12px] font-semibold border border-slate-200 px-4 py-2 rounded-lg text-slate-600 bg-white hover:bg-slate-50 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" />
            Weekly brief → PDF
          </button>
        </div>

      </div>
    </div>
  );
}
