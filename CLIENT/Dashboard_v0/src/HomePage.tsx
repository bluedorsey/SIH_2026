import { ArrowRight, Zap, RefreshCw, BarChart2, Network, MapPin, Shield, FileText, Layers } from "lucide-react";
import { reports } from "./data";

const QUICK_NAV = [
  { id: "sif-triage",         Icon: Layers,    title: "SIF-Precursor Triage", desc: "Triage queue, heatmap, act-first alerts"    },
  { id: "risk-dashboard",     Icon: BarChart2, title: "Risk Dashboard",        desc: "Density, site rankings, trend charts"        },
  { id: "precursor-patterns", Icon: Network,   title: "Precursor Patterns",    desc: "Recurring failure modes across activities"   },
  { id: "site-intelligence",  Icon: MapPin,    title: "Sites & Activities",    desc: "Spatial risk maps and zone breakdowns"       },
  { id: "lsr",                Icon: Shield,    title: "Life-Saving Rules",     desc: "IOGP LSR compliance and SIF mapping"         },
  { id: "reports",            Icon: FileText,  title: "Reports",               desc: "Searchable HSSE observation explorer"        },
];

const HIGH_ALERTS = reports.filter((r) => r.priority === "HIGH").slice(0, 3);

/* ═══════════════════════════ HOME PAGE ═══════════════════════════ */
export default function HomePage({ onNavigate }: { onNavigate: (s: string) => void }) {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>

      {/* ── Greeting ── */}
      <div className="px-6 pt-6 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">{greeting}, HSE Administrator</h1>
        <p className="text-slate-400 text-sm mt-1">Here is what is happening across your sites today.</p>
      </div>

      {/* ── KPI strip ── */}
      <div className="px-6 grid grid-cols-4 gap-3 mb-5">
        {[
          { value: "9",     label: "P-SIF this week",       sub: "▲ 12% vs last week",          accent: "#dc2626" },
          { value: "23.6%", label: "SIF precursor density", sub: "Across all active sites",      accent: "#d97706" },
          { value: "14",    label: "Sites affected",        sub: "6 field sites monitored",      accent: "#0d5555" },
          { value: "23",    label: "Awaiting review",       sub: "Oldest 3 days · est. 45 min", accent: "#2563eb" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-slate-100 px-4 py-3.5 shadow-sm">
            <div className="text-2xl font-black font-mono tracking-tight" style={{ color: k.accent }}>{k.value}</div>
            <div className="text-xs font-semibold text-slate-600 mt-0.5">{k.label}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">{k.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Two-column row ── */}
      <div className="px-6 grid grid-cols-2 gap-4 mb-5">

        {/* Needs attention */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100">
            <h2 className="font-bold text-slate-800 text-sm">Needs your attention</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Top unreviewed high-risk P-SIF alerts</p>
          </div>
          <div className="divide-y divide-slate-50">
            {HIGH_ALERTS.map((r) => (
              <div key={r.id} className="px-5 py-3.5 flex items-start gap-3 hover:bg-red-50/30 transition-colors">
                <span className="w-2 h-2 rounded-full bg-red-500 mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold text-slate-800 leading-snug">{r.title}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5 font-mono">{r.id} · {r.site} · {r.reportedAgo}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50">
            <button
              onClick={() => onNavigate("sif-triage")}
              className="text-[12px] font-semibold flex items-center gap-1 hover:opacity-70 transition-opacity"
              style={{ color: "#0d5555" }}>
              View all in SIF-Precursor Triage <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* AI Model Status */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-cyan-500" />
            <h2 className="font-bold text-slate-800 text-sm">AI Model Status</h2>
          </div>
          <div className="px-5 py-4 space-y-3">
            {([
              ["Status",             <span key="s" className="flex items-center gap-1.5 font-semibold text-emerald-600"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />Operational</span>],
              ["NLP version",        <span key="v" className="font-mono text-slate-800">v3.2</span>],
              ["Last sync",          <span key="ls" className="font-mono text-slate-800">2 min ago</span>],
              ["Model accuracy",     <span key="a" className="font-mono text-emerald-600 font-semibold">94.1%</span>],
              ["Pending ingestion",  <span key="p" className="font-mono text-amber-600 font-semibold">3 reports</span>],
              ["Rule engine",        <span key="r" className="font-mono text-slate-800">policy_table_v4.yaml</span>],
            ] as [string, React.ReactNode][]).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-0.5">
                <span className="text-[12px] text-slate-500">{k}</span>
                <span className="text-[12.5px] text-slate-800">{v}</span>
              </div>
            ))}
          </div>
          <div className="px-5 pb-4">
            <button
              onClick={() => onNavigate("system")}
              className="text-[12px] font-semibold flex items-center gap-1 hover:opacity-70 transition-opacity"
              style={{ color: "#0d5555" }}>
              Go to Administration <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Quick navigation tiles ── */}
      <div className="px-6 mb-5">
        <h2 className="font-bold text-slate-600 text-xs uppercase tracking-widest mb-3">Quick navigation</h2>
        <div className="grid grid-cols-6 gap-3">
          {QUICK_NAV.map(({ id, Icon, title, desc }) => (
            <button key={id} onClick={() => onNavigate(id)}
              className="bg-white border border-slate-100 rounded-xl p-4 text-left hover:border-cyan-200 hover:shadow-md transition-all shadow-sm group">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3 transition-colors group-hover:bg-cyan-50"
                style={{ background: "rgba(0,201,201,0.08)" }}>
                <Icon className="w-4 h-4" style={{ color: "#0d5555" }} />
              </div>
              <div className="font-bold text-slate-800 text-[12.5px] mb-1 leading-snug">{title}</div>
              <div className="text-[10.5px] text-slate-400 leading-snug">{desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Footer strip ── */}
      <div className="px-6 pb-6 flex items-center gap-1.5 text-[11px] text-slate-400">
        <RefreshCw className="w-3 h-3" />
        Data last synced 2 min ago · All systems operational
      </div>

    </div>
  );
}
