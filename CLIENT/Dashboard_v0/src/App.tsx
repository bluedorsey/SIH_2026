import { useState } from "react";
import {
  LayoutDashboard, BarChart2, Network, MapPin, Shield, FileText,
  Settings, Bell, ChevronDown, ChevronRight, TrendingUp, TrendingDown,
  Minus, Download, Filter, X, CheckCircle, Clock, AlertTriangle,
  Info, Activity, ArrowRight, MessageSquare, Search, RefreshCw,
  Eye, UserCheck, Zap, Layers, Home, Server,
  // LSR icons
  Plug, Construction, Lock, Flame, Crosshair, MoveUp, Truck, HardHat,
} from "lucide-react";
import SifTriageDashboard from "./SifTriageDashboard";
import SystemPage from "./SystemPage";
import HomePage from "./HomePage";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, BarChart, Bar, Cell,
} from "recharts";
import {
  reports, patterns, siteData, trendData, activityData, lsrData,
  notifications, type Report, type RiskLevel,
} from "./data";

type Screen = "home" | "report-detail" | "risk-dashboard" | "precursor-patterns" | "lsr" | "site-intelligence" | "reports" | "sif-triage" | "system";

/* ─── TOKENS ─── */
const RISK = {
  HIGH:    { bg: "bg-red-600",    pill: "bg-red-50 text-red-700 border border-red-200",    dot: "bg-red-500",    text: "text-red-600"    },
  REVIEW:  { bg: "bg-amber-500",  pill: "bg-amber-50 text-amber-700 border border-amber-200", dot: "bg-amber-400", text: "text-amber-600"  },
  ROUTINE: { bg: "bg-emerald-500",pill: "bg-emerald-50 text-emerald-700 border border-emerald-200", dot: "bg-emerald-500", text: "text-emerald-600" },
} as const;

/* ─── SHARED COMPONENTS ─── */
function RiskPill({ level, size = "sm" }: { level: RiskLevel; size?: "sm" | "md" | "lg" }) {
  const sz = { sm: "text-[10px] px-2 py-0.5 font-bold", md: "text-xs px-2.5 py-1 font-bold", lg: "text-sm px-3 py-1.5 font-bold" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full tracking-wide ${RISK[level].pill} ${sz[size]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${RISK[level].dot} shrink-0`} />
      {level}
    </span>
  );
}

function ConfBar({ value, color }: { value: number; color?: string }) {
  const c = color ?? (value >= 85 ? "#00c9c9" : value >= 70 ? "#d97706" : "#94a3b8");
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: c }} />
      </div>
      <span className="text-[11px] font-mono font-semibold text-slate-500 w-7">{value}%</span>
    </div>
  );
}

function TrendBadge({ v }: { v: "up" | "flat" | "down" | number }) {
  const up = v === "up" || (typeof v === "number" && v > 0);
  const dn = v === "down" || (typeof v === "number" && v < 0);
  if (up) return <TrendingUp className="w-3.5 h-3.5 text-red-400" />;
  if (dn) return <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />;
  return <Minus className="w-3.5 h-3.5 text-slate-400" />;
}

/* ─── SIDEBAR ─── */
const NAV = [
  { id: "home" as Screen,              icon: <Home            className="w-4 h-4" />, label: "Home"                 },
  { id: "sif-triage" as Screen,        icon: <Layers          className="w-4 h-4" />, label: "SIF-Precursor Triage", badge: 9  },
  { id: "risk-dashboard" as Screen,    icon: <BarChart2        className="w-4 h-4" />, label: "Risk Dashboard"       },
  { id: "precursor-patterns" as Screen,icon: <Network          className="w-4 h-4" />, label: "Precursor Patterns"   },
  { id: "site-intelligence" as Screen, icon: <MapPin           className="w-4 h-4" />, label: "Sites & Activities"   },
  { id: "lsr" as Screen,               icon: <Shield           className="w-4 h-4" />, label: "Life-Saving Rules"    },
  { id: "reports" as Screen,           icon: <FileText         className="w-4 h-4" />, label: "Reports"              },
];

/* ── Tooltip wrapper for collapsed nav items ── */
function NavTooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="relative group/tip flex justify-center">
      {children}
      <div className="pointer-events-none absolute left-full ml-3 top-1/2 -translate-y-1/2 z-50
        whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[11px] font-semibold text-white shadow-xl
        opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150"
        style={{ background: "#0a4040", border: "1px solid rgba(0,201,201,0.2)" }}>
        {label}
        {/* left arrow */}
        <span className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent"
          style={{ borderRightColor: "#0a4040" }} />
      </div>
    </div>
  );
}

function Sidebar({
  active, onNavigate, notifOpen, setNotifOpen, collapsed, onToggle,
}: {
  active: Screen; onNavigate: (s: Screen) => void;
  notifOpen: boolean; setNotifOpen: (v: boolean) => void;
  collapsed: boolean; onToggle: () => void;
}) {
  return (
    <aside
      className="shrink-0 flex flex-col h-full sidebar-scroll overflow-y-auto overflow-x-hidden"
      style={{
        background: "#072e2e",
        width: collapsed ? 64 : 224,
        transition: "width 250ms ease",
        minWidth: collapsed ? 64 : 224,
      }}
    >
      {/* ── Brand row ── */}
      <div className={`pt-4 pb-3 flex items-center ${collapsed ? "justify-center px-0 flex-col gap-2" : "px-4 justify-between"}`}>
        {/* OIL logo */}
        <div
          className="w-9 h-9 rounded-full shrink-0 flex items-center justify-center"
          style={{
            background: "conic-gradient(from 0deg,#e86c1a 0%,#c82020 40%,#e86c1a 70%,#c82020 100%)",
            boxShadow: "0 0 0 2px #0a4040,0 0 0 3px rgba(232,108,26,0.4)",
          }}
        >
          <span className="text-white font-black text-[10px] tracking-tight leading-none text-center">
            OIL<br /><span className="text-[7px] font-semibold opacity-90">INDIA</span>
          </span>
        </div>

        {/* Wordmark — hidden when collapsed */}
        {!collapsed && (
          <div className="flex-1 min-w-0 ml-2">
            <div className="text-white font-bold text-sm leading-tight">Oil India Ltd.</div>
            <div className="text-[10px] leading-tight" style={{ color: "#00c9c9" }}>HSSE Intelligence</div>
          </div>
        )}

        {/* Toggle button */}
        <button
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center transition-colors hover:bg-white/10"
          style={{ color: "rgba(255,255,255,0.35)" }}
        >
          {/* Animated chevron */}
          <svg
            width="14" height="14" viewBox="0 0 14 14" fill="none"
            style={{ transform: collapsed ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 250ms ease" }}
          >
            <path d="M9 2L4 7L9 12" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* Platform label — hidden when collapsed */}
      {!collapsed && (
        <div className="mx-4 mt-0 mb-3 pt-3 border-t border-white/5">
          <div className="text-[9px] font-bold uppercase tracking-widest mb-0.5" style={{ color: "rgba(0,201,201,0.5)" }}>Platform</div>
          <div className="text-white font-semibold text-sm leading-tight">SIF Precursor</div>
          <div className="font-bold text-sm" style={{ color: "#00c9c9" }}>Intelligence</div>
        </div>
      )}

      {/* Search — hidden when collapsed */}
      {!collapsed && (
        <div className="px-4 mb-3">
          <div className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ background: "rgba(255,255,255,0.06)" }}>
            <Search className="w-3.5 h-3.5 text-white/30 shrink-0" />
            <input placeholder="Search reports…" className="bg-transparent text-white/60 text-xs outline-none placeholder-white/25 w-full" />
          </div>
        </div>
      )}

      {/* ── Nav ── */}
      <nav className={`flex-1 ${collapsed ? "px-1" : "px-2"}`}>
        {NAV.map((item) => {
          const isActive = active === item.id;
          const btn = (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center rounded-lg mb-0.5 transition-all group relative
                ${collapsed ? "justify-center px-0 py-3" : "gap-3 px-3 py-2.5 text-left"}
                ${isActive ? "nav-active" : "hover:bg-white/5"}`}
            >
              <span className={`shrink-0 ${isActive ? "text-cyan-400" : "text-white/35 group-hover:text-white/60"}`}>
                {item.icon}
              </span>
              {!collapsed && (
                <>
                  <span className={`text-[13px] font-medium flex-1 ${isActive ? "text-white" : "text-white/50 group-hover:text-white/80"}`}>
                    {item.label}
                  </span>
                  {item.badge && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-red-600 text-white shrink-0">{item.badge}</span>
                  )}
                </>
              )}
              {/* Badge dot in collapsed state */}
              {collapsed && item.badge && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
              )}
            </button>
          );
          return collapsed
            ? <NavTooltip key={item.id} label={item.label}>{btn}</NavTooltip>
            : btn;
        })}

        {/* System + Administration */}
        <div className={`mt-2 border-t border-white/5 pt-2`}>
          {/* System nav item */}
          {(() => {
            const isSystemActive = active === "system";
            const sysBtn = (
              <button
                onClick={() => onNavigate("system")}
                className={`w-full flex items-center rounded-lg mb-0.5 transition-all group relative
                  ${collapsed ? "justify-center px-0 py-3" : "gap-3 px-3 py-2.5 text-left"}
                  ${isSystemActive ? "nav-active" : "hover:bg-white/5"}`}
              >
                <span className={`shrink-0 ${isSystemActive ? "text-cyan-400" : "text-white/35 group-hover:text-white/60"}`}>
                  <Server className="w-4 h-4" />
                </span>
                {!collapsed && (
                  <span className={`text-[13px] font-medium flex-1 ${isSystemActive ? "text-white" : "text-white/50 group-hover:text-white/80"}`}>
                    System
                  </span>
                )}
              </button>
            );
            return collapsed ? <NavTooltip key="system" label="System">{sysBtn}</NavTooltip> : sysBtn;
          })()}

          {/* Administration */}
          {collapsed ? (
            <NavTooltip label="Administration">
              <button className="w-full flex items-center justify-center py-3 rounded-lg hover:bg-white/5 transition-all group">
                <Settings className="w-4 h-4 text-white/30 group-hover:text-white/60" />
              </button>
            </NavTooltip>
          ) : (
            <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-white/5 transition-all group">
              <Settings className="w-4 h-4 text-white/30 group-hover:text-white/60 shrink-0" />
              <span className="text-[13px] font-medium text-white/40 group-hover:text-white/70">Administration</span>
            </button>
          )}
        </div>
      </nav>

      {/* ── AI Status ── */}
      <div className={`pb-3 ${collapsed ? "px-1" : "px-3"}`}>
        {collapsed ? (
          <NavTooltip label="AI Model: operational">
            <div className="flex justify-center py-2">
              <div className="relative">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 animate-pulse border border-[#072e2e]" />
              </div>
            </div>
          </NavTooltip>
        ) : (
          <div className="rounded-xl p-3" style={{ background: "rgba(0,201,201,0.07)", border: "1px solid rgba(0,201,201,0.12)" }}>
            <div className="flex items-center gap-2 mb-1.5">
              <Zap className="w-3 h-3 text-cyan-400" />
              <span className="text-[9px] font-bold uppercase tracking-widest text-cyan-500/70">AI Model Status</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span className="text-white text-[11px] font-semibold">Model operational</span>
            </div>
            <div className="text-white/25 text-[9px] mt-0.5">NLP v3.2 · Sync 2m ago</div>
          </div>
        )}
      </div>

      {/* ── User ── */}
      <div className={`border-t border-white/5 pt-3 pb-4 ${collapsed ? "px-1" : "px-4"}`}>
        {collapsed ? (
          <NavTooltip label="HSE Administrator — OIL Corporate HSSE">
            <button
              onClick={() => setNotifOpen(!notifOpen)}
              className="relative flex items-center justify-center py-1"
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white"
                style={{ background: "linear-gradient(135deg,#e86c1a,#c82020)" }}
              >
                HA
              </div>
              {/* notification dot */}
              <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-red-500 rounded-full border border-[#072e2e]" />
            </button>
          </NavTooltip>
        ) : (
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold text-white"
              style={{ background: "linear-gradient(135deg,#e86c1a,#c82020)" }}
            >
              HA
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-[11px] font-semibold truncate">HSE Administrator</div>
              <div className="text-white/35 text-[9px] truncate">OIL Corporate HSSE</div>
            </div>
            <button onClick={() => setNotifOpen(!notifOpen)} className="relative text-white/30 hover:text-cyan-400 transition-colors shrink-0">
              <Bell className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-500 rounded-full text-[8px] text-white flex items-center justify-center font-bold">4</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

/* ─── TOP BAR ─── */
function TopBar({ screen, reportId }: { screen: Screen; reportId?: string }) {
  const labels: Record<Screen, string> = {
    "home": "Home",
    "report-detail": `Report ${reportId ?? ""}`,
    "sif-triage": "SIF-Precursor Triage",
    "risk-dashboard": "Risk Dashboard",
    "precursor-patterns": "Precursor Patterns",
    "lsr": "Life-Saving Rules",
    "site-intelligence": "Site Intelligence",
    "reports": "Reports",
    "system": "System",
  };
  return (
    <header className="h-11 bg-white border-b border-slate-100 flex items-center justify-between px-5 shrink-0">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-400">OIL HSSE</span>
        <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
        <span className="text-slate-700 font-semibold">{labels[screen]}</span>
      </div>
      <div className="flex items-center gap-4 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5"><RefreshCw className="w-3 h-3" /> Updated 2 min ago</div>
        <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> All systems operational</div>
        <div className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-500 cursor-pointer hover:bg-slate-50">
          Last 30 days <ChevronDown className="w-3 h-3" />
        </div>
        <div className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-500 cursor-pointer hover:bg-slate-50">
          All Sites <ChevronDown className="w-3 h-3" />
        </div>
      </div>
    </header>
  );
}

/* ─── KPI CARD ─── */
function KPI({ value, label, sub, accent }: { value: string | number; label: string; sub?: string; accent?: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 px-4 py-3.5 shadow-sm">
      <div className="text-2xl font-black font-mono tracking-tight" style={{ color: accent ?? "#0d5555" }}>{value}</div>
      <div className="text-xs font-semibold text-slate-600 mt-0.5">{label}</div>
      {sub && <div className="text-[10px] text-slate-400 mt-0.5">{sub}</div>}
    </div>
  );
}

/* ═══════════════════════════ TRIAGE QUEUE ═══════════════════════════ */
/* ═══════════════════════════ REPORT DETAIL ═══════════════════════════ */
function CausalStep({ label, val, accent, last }: { label: string; val: string; accent: string; last?: boolean }) {
  return (
    <div className="flex flex-col items-stretch">
      <div className="rounded-xl px-4 py-3 border-l-4" style={{ background: `${accent}0d`, borderLeftColor: accent }}>
        <div className="text-[9px] font-bold tracking-widest uppercase mb-0.5" style={{ color: accent }}>{label}</div>
        <div className="text-sm font-semibold text-slate-800">{val}</div>
      </div>
      {!last && (
        <div className="flex flex-col items-center py-1">
          <div className="w-px h-3 bg-slate-200" />
          <ChevronRight className="w-3.5 h-3.5 text-slate-300 rotate-90 -mt-0.5" />
        </div>
      )}
    </div>
  );
}

function ReportDetail({ report, onBack }: { report: Report; onBack: () => void }) {
  const [action, setAction] = useState<string | null>(null);
  const isReview = report.priority === "REVIEW";
  const signals = [
    { l: "Hazard severity", v: 91 }, { l: "Exposure", v: 94 },
    { l: "Energy level", v: 97 },    { l: "Barrier failure", v: 98 },
    { l: "Consequence potential", v: 95 },
  ];

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      {/* Back bar */}
      <div className="bg-white border-b border-slate-100 px-6 py-2.5 flex items-center gap-2">
        <button onClick={onBack} className="flex items-center gap-1.5 text-xs font-semibold transition-colors hover:text-slate-900" style={{ color: "#0d5555" }}>
          <ChevronRight className="w-3.5 h-3.5 rotate-180" /> Back to Triage Queue
        </button>
        <span className="text-slate-200">·</span>
        <span className="text-xs text-slate-400 font-mono">{report.id}</span>
      </div>

      {/* Header */}
      <div className="px-6 py-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            {report.priority !== "ROUTINE" && (
              <span className="flex items-center gap-1.5 bg-red-600 text-white text-[11px] font-bold px-2.5 py-1 rounded-lg uppercase tracking-wide">
                <AlertTriangle className="w-3 h-3" /> SIF Potential — {report.priority}
              </span>
            )}
            <RiskPill level={report.priority} size="md" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">{report.title}</h1>
        </div>
        <div className="flex items-center gap-2">
          {isReview && <span className="flex items-center gap-1.5 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5 font-semibold"><Clock className="w-3.5 h-3.5" /> Human review required</span>}
          <span className="flex items-center gap-1.5 text-[11px] font-mono font-bold px-3 py-1.5 rounded-lg border" style={{ color: "#0d5555", borderColor: "rgba(0,201,201,0.3)", background: "rgba(0,201,201,0.07)" }}>
            <Activity className="w-3.5 h-3.5" /> {report.confidence}% confidence
          </span>
          <button className="text-white text-xs font-bold px-4 py-1.5 rounded-lg" style={{ background: "#0d5555" }}>Assign Review</button>
          <button className="text-slate-600 text-xs font-semibold px-4 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50">Mark Reviewed</button>
        </div>
      </div>

      <div className="px-6 pb-6 grid grid-cols-3 gap-4">
        {/* Left 2/3 */}
        <div className="col-span-2 space-y-4">
          {/* Original report */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">Original Report</div>
            <blockquote className="border-l-4 pl-4 text-slate-700 text-[15px] leading-relaxed italic" style={{ borderColor: "#00c9c9" }}>
              "{report.originalText}"
            </blockquote>
            <div className="grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-100">
              {[["Report type",report.reportType],["Site",report.site],["Location",report.location],["Activity",report.activity],["Reported by",report.reportedBy],["Date",report.date],["AI processed","12:42 PM"]].map(([k,v]) => (
                <div key={k}>
                  <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">{k}</div>
                  <div className="text-xs font-semibold text-slate-800 mt-0.5">{v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* AI explanation */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-5 h-5 rounded flex items-center justify-center" style={{ background: "#0d5555" }}>
                <Zap className="w-3 h-3 text-cyan-300" />
              </div>
              <h2 className="font-bold text-slate-800 text-sm">Why did AI classify this as {report.priority}?</h2>
              <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full" style={{ background: "rgba(0,201,201,0.1)", color: "#0d5555" }}>AI Detected</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Hazard", val: report.hazard, accent: "#dc2626", desc: "High-energy object capable of causing severe injury or fatality." },
                { label: "Exposure", val: "Personnel potentially within lifting area", accent: "#e86c1a", desc: "Workers may be exposed to dropped-load / struck-by risk." },
                { label: "Required Barrier", val: "Banksman / exclusion zone", accent: "#2563eb", desc: "Required control for safe lifting operation." },
                { label: "Control State", val: report.barrierFailure, accent: "#d97706", desc: "Report indicates no banksman was present." },
              ].map((c) => (
                <div key={c.label} className="rounded-xl p-4 border-l-4" style={{ background: `${c.accent}0d`, borderLeftColor: c.accent }}>
                  <div className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: c.accent }}>{c.label}</div>
                  <div className="text-sm font-bold text-slate-800 mb-1">{c.val}</div>
                  <div className="text-[11px] text-slate-500 leading-relaxed">{c.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Human-in-loop */}
          {isReview && !action && (
            <div className="bg-white rounded-xl border-2 border-amber-200 shadow-sm p-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-4.5 h-4.5 text-amber-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold text-amber-600 uppercase tracking-widest">AI Recommendation</span>
                    <RiskPill level="REVIEW" />
                    <span className="text-[11px] font-mono text-slate-400">{report.confidence}% confidence</span>
                  </div>
                  <p className="text-sm text-slate-700 font-semibold mb-0.5">Possible SIF precursor</p>
                  <p className="text-xs text-slate-500 mb-4">"Evidence is insufficient to confidently determine SIF potential. Human review recommended to determine classification."</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {[
                      { label: "Confirm SIF Potential", icon: <AlertTriangle className="w-3.5 h-3.5" />, style: "bg-red-600 text-white", action: "confirmed" },
                      { label: "Mark Non-SIF", icon: <CheckCircle className="w-3.5 h-3.5" />, style: "bg-emerald-600 text-white", action: "non-sif" },
                      { label: "Request Investigation", icon: <Search className="w-3.5 h-3.5" />, style: "border border-slate-200 text-slate-700 bg-white hover:bg-slate-50", action: null },
                      { label: "Add Comment", icon: <MessageSquare className="w-3.5 h-3.5" />, style: "border border-slate-200 text-slate-700 bg-white hover:bg-slate-50", action: null },
                    ].map((btn) => (
                      <button key={btn.label} onClick={() => btn.action && setAction(btn.action)}
                        className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${btn.style}`}>
                        {btn.icon} {btn.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
          {action && (
            <div className={`rounded-xl px-4 py-3 flex items-center gap-2 border ${action === "confirmed" ? "bg-red-50 border-red-200" : "bg-emerald-50 border-emerald-200"}`}>
              <CheckCircle className={`w-4 h-4 ${action === "confirmed" ? "text-red-600" : "text-emerald-600"}`} />
              <span className="text-sm font-semibold text-slate-800">
                {action === "confirmed" ? "Classified as SIF Potential by human reviewer." : "Marked as Non-SIF by human reviewer."}
              </span>
              <button onClick={() => setAction(null)} className="ml-auto text-slate-400"><X className="w-4 h-4" /></button>
            </div>
          )}

          {/* Confidence */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-800 text-sm">AI Classification Confidence</h3>
              <div className="flex items-center gap-2">
                <div className="text-2xl font-black font-mono" style={{ color: "#0d5555" }}>{report.confidence}%</div>
                <button className="text-slate-300 hover:text-slate-500"><Info className="w-4 h-4" /></button>
              </div>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-4">
              <div className="h-full rounded-full" style={{ width: `${report.confidence}%`, background: "linear-gradient(90deg,#00c9c9,#0d5555)" }} />
            </div>
            <div className="space-y-2.5">
              {signals.map((s) => (
                <div key={s.l} className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500 w-36 shrink-0">{s.l}</span>
                  <div className="flex-1"><ConfBar value={s.v} color="#00c9c9" /></div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 rounded-xl text-[11px] text-slate-500 leading-relaxed" style={{ background: "rgba(0,201,201,0.05)", border: "1px solid rgba(0,201,201,0.12)" }}>
              Confidence indicates how strongly detected features support the classification. It does not represent probability of an incident occurring.
            </div>
          </div>
        </div>

        {/* Right 1/3 */}
        <div className="space-y-4">
          {/* Causal chain */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <h3 className="font-bold text-slate-800 text-sm mb-4 flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-red-500" /> Fatal Potential Chain
            </h3>
            <CausalStep label="Hazard" val={report.hazard} accent="#dc2626" />
            <CausalStep label="Exposure" val="Personnel near lifting area" accent="#e86c1a" />
            <CausalStep label="Required Barrier" val="Banksman + exclusion zone" accent="#2563eb" />
            <CausalStep label="Barrier Failure" val={report.barrierFailure} accent="#d97706" />
            <CausalStep label="Potential Consequence" val="Struck-by / dropped load" accent="#dc2626" />
            <div className="mt-1">
              <div className="flex flex-col items-center py-1"><div className="w-px h-3 bg-red-300" /><ChevronRight className="w-3.5 h-3.5 text-red-300 rotate-90 -mt-0.5" /></div>
              <div className="rounded-xl px-4 py-3 flex items-center gap-2 bg-red-600 text-white">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <div><div className="text-[9px] font-bold uppercase tracking-widest opacity-70">SIF POTENTIAL</div><div className="font-black">HIGH</div></div>
              </div>
              <div className="flex flex-col items-center py-1"><div className="w-px h-3 bg-slate-200" /><ChevronRight className="w-3.5 h-3.5 text-slate-300 rotate-90 -mt-0.5" /></div>
              <div className="rounded-xl px-4 py-3 flex items-center gap-2 border" style={{ background: "rgba(0,201,201,0.07)", borderColor: "rgba(0,201,201,0.2)" }}>
                <Shield className="w-4 h-4 shrink-0" style={{ color: "#0d5555" }} />
                <div><div className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "#00c9c9" }}>Life-Saving Rule</div><div className="font-bold text-slate-800 text-sm">{report.lsr}</div></div>
              </div>
            </div>
          </div>

          {/* LSR card */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <h3 className="font-bold text-slate-800 text-sm mb-3">AI-Mapped Life-Saving Rule</h3>
            <div className="flex items-center gap-3 mb-3">
              <div className="text-4xl">🏗️</div>
              <div>
                <div className="font-bold text-slate-800">{report.lsr}</div>
                <div className="text-[11px] font-mono font-bold mt-0.5" style={{ color: "#00c9c9" }}>98% match</div>
              </div>
            </div>
            {["Suspended load","Lifting activity","Personnel exposure","Banksman requirement"].map((s) => (
              <div key={s} className="flex items-center gap-2 text-[11px] text-slate-600 mb-1.5">
                <CheckCircle className="w-3 h-3 shrink-0" style={{ color: "#00c9c9" }} /> {s}
              </div>
            ))}
            <button className="w-full mt-3 text-xs font-bold py-1.5 rounded-lg border transition-colors hover:opacity-80"
              style={{ color: "#0d5555", background: "rgba(0,201,201,0.08)", borderColor: "rgba(0,201,201,0.2)" }}>
              View Life-Saving Rule →
            </button>
            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-2">Secondary possibilities</div>
              {[{ n: "Line of Fire", p: 21 }, { n: "Energy Isolation", p: 4 }].map((s) => (
                <div key={s.n} className="flex items-center gap-2 mb-1.5">
                  <span className="text-[11px] text-slate-500 w-28">{s.n}</span>
                  <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-slate-300 rounded-full" style={{ width: `${s.p}%` }} />
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 w-6">{s.p}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════ RISK DASHBOARD ═══════════════════════════ */
function RiskDashboard() {
  const [toggle, setToggle] = useState<"volume"|"density">("volume");
  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      <div className="px-6 pt-5 pb-3">
        <h1 className="text-xl font-bold text-slate-800">Risk Intelligence</h1>
        <p className="text-slate-400 text-xs mt-0.5">Where are SIF precursors concentrating?</p>
      </div>

      {/* Filters */}
      <div className="px-6 mb-4 flex flex-wrap gap-2">
        {[["Date Range","Last 30 days"],["Site","All Sites"],["Activity","All Activities"],["LSR","All Rules"],["Report Type","All Types"],["Risk","All Levels"]].map(([l,v]) => (
          <button key={l} className="flex items-center gap-1 text-[11px] text-slate-500 border border-slate-200 bg-white px-2.5 py-1.5 rounded-lg hover:bg-slate-50">
            <span className="text-slate-400">{l}:</span>{v}<ChevronDown className="w-3 h-3 ml-0.5" />
          </button>
        ))}
      </div>

      {/* KPIs */}
      <div className="px-6 grid grid-cols-4 gap-3 mb-4">
        <KPI value={118}    label="SIF-potential reports" accent="#dc2626" />
        <KPI value="23.6%"  label="SIF precursor density"  accent="#d97706" />
        <KPI value={14}     label="Sites affected" />
        <KPI value={7}      label="Recurring precursor patterns" accent="#2563eb" />
      </div>

      {/* Charts row */}
      <div className="px-6 grid grid-cols-3 gap-4 mb-4">
        {/* Line chart */}
        <div className="col-span-2 bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <h2 className="font-bold text-slate-800 text-sm mb-0.5">SIF-potential reports over time</h2>
          <p className="text-[11px] text-slate-400 mb-4">Monthly — total observations vs SIF-potential</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#94a3b8" }} />
              <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} />
              <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #e2e8f0" }} />
              <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="total" stroke="#cbd5e1" strokeWidth={2} dot={false} name="Total" />
              <Line type="monotone" dataKey="sif" stroke="#dc2626" strokeWidth={2.5} dot={{ r: 3, fill: "#dc2626" }} name="SIF-potential" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Bar chart */}
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-bold text-slate-800 text-sm">Activity breakdown</h2>
            <div className="flex rounded-lg overflow-hidden border border-slate-200 text-[10px]">
              {(["volume","density"] as const).map((t) => (
                <button key={t} onClick={() => setToggle(t)}
                  className={`px-2 py-1 capitalize transition-colors ${toggle === t ? "text-white font-semibold" : "text-slate-500 hover:bg-slate-50"}`}
                  style={toggle === t ? { background: "#0d5555" } : {}}>
                  {t === "volume" ? "Volume" : "Density"}
                </button>
              ))}
            </div>
          </div>
          <p className="text-[10px] text-slate-400 mb-3">Activities generating most SIF precursors</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={activityData} layout="vertical" margin={{ top: 0, right: 8, left: -8, bottom: 0 }}>
              <XAxis type="number" tick={{ fontSize: 9, fill: "#94a3b8" }} />
              <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 9, fill: "#64748b" }} />
              <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
              <Bar dataKey={toggle === "volume" ? "value" : "sifCount"} radius={[0,4,4,0]}>
                {activityData.map((_,i) => (
                  <Cell key={i} fill={["#dc2626","#e86c1a","#d97706","#ca8a04","#0d5555","#178080"][i] ?? "#94a3b8"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Site table */}
      <div className="px-6 pb-6">
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-bold text-slate-800 text-sm">Sites ranked by SIF precursor density</h2>
            <span className="text-[11px] text-slate-400">14 sites monitored</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
                {["#","Site","Reports","SIF Potential","Density","Trend","Risk"].map((h,i) => (
                  <th key={h} className={`py-2.5 ${i===0?"px-5 w-8":i<4?"px-4":"px-4 text-center"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {siteData.map((s,i) => (
                <tr key={s.name} className="border-b border-slate-50 hover:bg-cyan-50/20 transition-colors">
                  <td className="px-5 py-3 text-[11px] font-mono text-slate-400">{String(i+1).padStart(2,"0")}</td>
                  <td className="px-4 py-3 font-semibold text-slate-800 text-sm">{s.name}</td>
                  <td className="px-4 py-3 font-mono text-slate-600 text-sm">{s.reports}</td>
                  <td className="px-4 py-3">
                    <span className={`font-black font-mono text-sm ${s.risk==="HIGH"?"text-red-600":s.risk==="REVIEW"?"text-amber-600":"text-slate-600"}`}>{s.sifPotential}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${s.risk==="HIGH"?"bg-red-500":s.risk==="REVIEW"?"bg-amber-400":"bg-emerald-400"}`} style={{ width: `${s.density*2.5}%` }} />
                      </div>
                      <span className="font-mono text-[11px] text-slate-600">{s.density}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center"><TrendBadge v={s.trend} /></td>
                  <td className="px-4 py-3 text-center"><RiskPill level={s.risk} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════ PRECURSOR PATTERNS ═══════════════════════════ */
function PrecursorPatterns() {
  const [sel, setSel] = useState<string|null>(null);
  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      <div className="px-6 pt-5 pb-4">
        <h1 className="text-xl font-bold text-slate-800">Precursor Patterns</h1>
        <p className="text-slate-400 text-xs mt-0.5">What failure modes keep appearing?</p>
      </div>

      <div className="px-6 grid grid-cols-3 gap-4 mb-6">
        {patterns.map((p,i) => (
          <button key={p.id} onClick={() => setSel(sel===p.id?null:p.id)}
            className={`text-left rounded-xl p-5 border shadow-sm transition-all hover:shadow-md ${sel===p.id?"ring-2 ring-cyan-300 border-cyan-300 bg-cyan-50/30":"bg-white border-slate-100 hover:border-slate-200"}`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-mono font-bold text-slate-400">PATTERN {String(i+1).padStart(2,"0")}</span>
                <RiskPill level={p.riskLevel} />
              </div>
              <div className="flex items-center gap-1">
                <TrendBadge v={p.trend} />
                <span className={`text-[11px] font-bold ${p.trend>0?"text-red-500":"text-emerald-500"}`}>{p.trend>0?"+":""}{p.trend}%</span>
              </div>
            </div>
            <div className="font-bold text-slate-800 text-[13px] leading-snug mb-3">{p.title}</div>
            <div className="flex items-end gap-2 mb-2">
              <span className="text-3xl font-black font-mono" style={{ color: "#0d5555" }}>{p.occurrences}</span>
              <span className="text-xs text-slate-400 pb-1">occurrences</span>
            </div>
            <div className="flex flex-wrap gap-1 mb-2">
              {p.sites.map((s) => (
                <span key={s} className="text-[10px] rounded-full px-2 py-0.5 font-medium" style={{ background: "rgba(0,201,201,0.1)", color: "#0d5555" }}>{s}</span>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <Shield className="w-3 h-3" style={{ color: "#00c9c9" }} />
              <span className="text-[11px] font-semibold" style={{ color: "#0d5555" }}>{p.lsr}</span>
            </div>
          </button>
        ))}
      </div>

      {/* Pattern explorer */}
      <div className="px-6 pb-6">
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <h2 className="font-bold text-slate-800 text-sm mb-1">Pattern Explorer</h2>
          <p className="text-[11px] text-slate-400 mb-5">Activity → Hazard → Barrier Failure → Location → LSR — click any node to filter</p>
          <div className="overflow-x-auto pb-2">
            <div className="flex gap-px min-w-max">
              {[
                { title: "Activity",       color: "#072e2e", items: ["Lifting Operations","Energy Isolation","Confined Space","Hot Work"] },
                { title: "Hazard",         color: "#c82020", items: ["Suspended Load","Stored Energy","Hazardous Atmosphere","Ignition Source"] },
                { title: "Barrier Failure",color: "#e86c1a", items: ["Banksman absent","LOTO incomplete","Gas test skipped","Permit incomplete"] },
                { title: "Location",       color: "#d97706", items: ["Compressor Area","Wellhead","Processing Unit","Storage Area"] },
                { title: "LSR",            color: "#2563eb", items: ["Lifting Ops","Energy Isolation","Confined Space","Hot Work"] },
              ].map((col,ci) => (
                <div key={col.title} className="flex items-stretch">
                  <div className="w-40">
                    <div className="text-white text-[10px] font-bold uppercase tracking-widest px-3 py-2 rounded-t-xl" style={{ background: col.color }}>{col.title}</div>
                    <div className="border border-slate-100 rounded-b-xl overflow-hidden">
                      {col.items.map((item,ii) => (
                        <button key={item}
                          className={`w-full text-left px-3 py-2.5 text-xs border-b border-slate-50 last:border-0 transition-colors hover:text-white ${ii===0?"font-bold text-slate-700 bg-slate-50/80":"text-slate-500 hover:bg-opacity-90"}`}
                          style={ii===0?{}:{}}
                          onMouseEnter={(e) => { if(ii===0)(e.currentTarget as HTMLElement).style.background=col.color; (e.currentTarget as HTMLElement).style.color="#fff"; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background=""; (e.currentTarget as HTMLElement).style.color=""; }}>
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                  {ci < 4 && (
                    <div className="flex items-center px-1.5">
                      <div className="w-6 h-px bg-slate-200" />
                      <ChevronRight className="w-3 h-3 text-slate-300 -ml-1.5" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════ LIFE-SAVING RULES ═══════════════════════════ */
/* ── LSR icon map: one Lucide icon per rule, monochrome outline ── */
const LSR_ICON_MAP: Record<string, { Icon: React.ElementType; accent: string }> = {
  "Energy Isolation":  { Icon: Plug,         accent: "#2563eb" },
  "Lifting Operations":{ Icon: Construction, accent: "#0d5555" },
  "Confined Space":    { Icon: Lock,         accent: "#7c3aed" },
  "Hot Work":          { Icon: Flame,        accent: "#dc2626" },
  "Line of Fire":      { Icon: Crosshair,    accent: "#c0362c" },
  "Working at Height": { Icon: MoveUp,       accent: "#d97706" },
  "Driving":           { Icon: Truck,        accent: "#0369a1" },
  "PPE":               { Icon: HardHat,      accent: "#16a34a" },
};

function LsrIcon({ name, density }: { name: string; density: number }) {
  const entry = LSR_ICON_MAP[name];
  const accent = entry?.accent ?? (density > 50 ? "#dc2626" : density > 35 ? "#d97706" : "#16a34a");
  const Icon   = entry?.Icon ?? Shield;
  return (
    <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-3 shrink-0"
      style={{ background: `${accent}12`, border: `1.5px solid ${accent}28` }}>
      <Icon size={22} strokeWidth={1.75} color={accent} style={{ display: "block" }} />
    </div>
  );
}

function LifeSavingRules() {
  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      <div className="px-6 pt-5 pb-4">
        <h1 className="text-xl font-bold text-slate-800">Life-Saving Rules</h1>
        <p className="text-slate-400 text-xs mt-0.5">IOGP LSR compliance — SIF precursor mapping across all activities</p>
      </div>
      <div className="px-6 pb-6 grid grid-cols-4 gap-4">
        {lsrData.map((lsr) => {
          const accent = LSR_ICON_MAP[lsr.name]?.accent ?? (lsr.density > 50 ? "#dc2626" : lsr.density > 35 ? "#d97706" : "#16a34a");
          return (
          <div key={lsr.name} className="bg-white border border-slate-100 rounded-xl p-5 shadow-sm hover:shadow-md transition-all cursor-pointer group relative overflow-hidden">
            {/* Top accent bar */}
            <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: accent }} />
            <LsrIcon name={lsr.name} density={lsr.density} />
            <div className="font-bold text-slate-800 text-sm leading-snug mb-2">{lsr.name}</div>
            <div className="flex items-end gap-2 mb-2">
              <span className={`text-2xl font-black font-mono ${lsr.sifCount>=20?"text-red-600":lsr.sifCount>=10?"text-amber-600":"text-slate-700"}`}>{lsr.sifCount}</span>
              <span className="text-[10px] text-slate-400 pb-0.5">SIF precursors / {lsr.total} total</span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mb-3">
              <div className="h-full rounded-full" style={{ width: `${lsr.density}%`, background: lsr.density>50?"#dc2626":lsr.density>35?"#d97706":"#16a34a" }} />
            </div>
            <div className="flex justify-between text-[11px] text-slate-500 mb-1">
              <span>Density</span><span className="font-mono font-bold text-slate-700">{lsr.density}%</span>
            </div>
            <div className="flex justify-between text-[11px] text-slate-500 mb-3">
              <span>Trend</span>
              <div className="flex items-center gap-1">
                <TrendBadge v={lsr.trend} />
                <span className={`font-mono font-bold ${lsr.trend>0?"text-red-500":"text-emerald-500"}`}>{lsr.trend>0?"+":""}{lsr.trend}%</span>
              </div>
            </div>
            <div className="pt-3 border-t border-slate-100">
              <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">Top barrier failure</div>
              <div className="text-[11px] font-semibold text-orange-600 bg-orange-50 rounded-lg px-2 py-1">{lsr.topFailure}</div>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════ SITE INTELLIGENCE ═══════════════════════════ */
function SiteIntelligence() {
  const [selSpot, setSelSpot] = useState<string|null>(null);

  const hotspots = [
    { id:"comp", label:"Compressor Area", x:38, y:28, r:17, sif:6, p:"Suspended loads without exclusion zone", risk:"HIGH" as RiskLevel },
    { id:"well", label:"Wellhead",        x:65, y:42, r:12, sif:4, p:"Energy isolation not verified",         risk:"HIGH" as RiskLevel },
    { id:"proc", label:"Processing Unit", x:50, y:62, r:9,  sif:3, p:"Hot work near hydrocarbon lines",       risk:"REVIEW" as RiskLevel },
    { id:"work", label:"Workshop",        x:25, y:60, r:6,  sif:1, p:"PPE compliance issues",                 risk:"ROUTINE" as RiskLevel },
    { id:"stor", label:"Storage Area",    x:72, y:72, r:5,  sif:1, p:"Vehicle speed violations",             risk:"ROUTINE" as RiskLevel },
  ];

  const kpis = [["Total observations","184"],["SIF-potential","52"],["Near misses","31"],["Critical barriers failed","8"],["Open actions","14"]];

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      <div className="px-6 pt-5 pb-3 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Site Intelligence</h1>
          <p className="text-slate-400 text-xs mt-0.5">Spatial precursor concentration and site risk analytics</p>
        </div>
        <button className="flex items-center gap-1.5 text-sm font-semibold text-white px-3 py-1.5 rounded-lg" style={{ background: "#0d5555" }}>
          Site: Duliajan <ChevronDown className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="px-6 pb-6 grid grid-cols-4 gap-4">
        {/* Left panel */}
        <div className="space-y-4">
          {/* Risk score */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">Site Risk Score</div>
            <div className="flex items-end gap-2 mb-3">
              <div className="text-5xl font-black font-mono text-red-600">78</div>
              <div className="pb-1">
                <div className="text-sm text-slate-400">/ 100</div>
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500" /><span className="text-sm font-bold text-red-600">Elevated</span></div>
              </div>
            </div>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: "#f0f2f5" }}>
              <div className="h-full rounded-full" style={{ width: "78%", background: "linear-gradient(90deg,#d97706,#dc2626)" }} />
            </div>
          </div>
          {/* Site KPIs */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">Site KPIs</div>
            <div className="space-y-3">
              {kpis.map(([l,v]) => (
                <div key={l} className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">{l}</span>
                  <span className="text-sm font-black font-mono text-slate-800">{v}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Hotspot list */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">Zone Breakdown</div>
            {hotspots.map((h) => (
              <button key={h.id} onClick={() => setSelSpot(selSpot===h.id?null:h.id)}
                className={`w-full flex items-center justify-between py-2 border-b border-slate-50 last:border-0 transition-colors hover:bg-slate-50 rounded px-1 ${selSpot===h.id?"bg-cyan-50/50":""}`}>
                <span className="text-[11px] font-medium text-slate-600">{h.label}</span>
                <div className="flex items-center gap-1.5">
                  <span className={`text-[11px] font-mono font-bold ${h.risk==="HIGH"?"text-red-600":h.risk==="REVIEW"?"text-amber-600":"text-slate-600"}`}>{h.sif} SIF</span>
                  <RiskPill level={h.risk} />
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Map panel */}
        <div className="col-span-3 bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between" style={{ background: "#f8fafa" }}>
            <h2 className="font-bold text-slate-800 text-sm">Site Risk Map — Duliajan Field</h2>
            <div className="flex items-center gap-2 text-[10px] text-slate-400">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />HIGH</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" />REVIEW</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400" />ROUTINE</span>
              <span className="ml-2">· Number = SIF-potential count</span>
            </div>
          </div>

          {/* Map */}
          <div className="relative map-bg" style={{ height: 440 }}>
            {/* Facility SVG */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              {/* Roads */}
              <line x1="0" y1="50" x2="100" y2="50" stroke="rgba(0,201,201,0.15)" strokeWidth="0.5" />
              <line x1="50" y1="0" x2="50" y2="100" stroke="rgba(0,201,201,0.15)" strokeWidth="0.5" />
              <line x1="20" y1="0" x2="80" y2="100" stroke="rgba(0,201,201,0.08)" strokeWidth="0.3" strokeDasharray="2,3" />
              {/* Buildings */}
              {[
                { x:29,y:21,w:20,h:14,label:"Compressor" },
                { x:57,y:36,w:17,h:12,label:"Wellhead"   },
                { x:39,y:55,w:23,h:15,label:"Processing" },
                { x:15,y:53,w:17,h:12,label:"Workshop"   },
                { x:63,y:65,w:15,h:11,label:"Storage"    },
              ].map((b) => (
                <g key={b.label}>
                  <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="1.5"
                    fill="rgba(13,85,85,0.12)" stroke="rgba(0,201,201,0.25)" strokeWidth="0.5" />
                  <text x={b.x+b.w/2} y={b.y+b.h/2+1} textAnchor="middle" fontSize="2.8" fill="rgba(0,201,201,0.5)" fontWeight="600">{b.label}</text>
                </g>
              ))}
              {/* Pipeline */}
              <path d="M 38 28 Q 50 35 65 42" stroke="rgba(232,108,26,0.4)" strokeWidth="0.8" fill="none" strokeDasharray="1.5,1.5" />
              <path d="M 65 42 Q 58 50 50 62" stroke="rgba(232,108,26,0.3)" strokeWidth="0.8" fill="none" strokeDasharray="1.5,1.5" />
            </svg>

            {/* Hotspot markers */}
            {hotspots.map((h) => (
              <button key={h.id} onClick={() => setSelSpot(selSpot===h.id?null:h.id)}
                className="absolute transform -translate-x-1/2 -translate-y-1/2"
                style={{ left:`${h.x}%`, top:`${h.y}%` }}>
                {h.risk==="HIGH" && (
                  <div className="absolute inset-0 rounded-full bg-red-500 pulse-ring opacity-40 w-6 h-6" />
                )}
                <div className={`relative w-7 h-7 rounded-full border-2 border-white shadow-lg flex items-center justify-center font-black text-white text-[10px] z-10 transition-transform hover:scale-110 ${h.risk==="HIGH"?"bg-red-500":h.risk==="REVIEW"?"bg-amber-400":"bg-emerald-500"}`}>
                  {h.sif}
                </div>
              </button>
            ))}

            {/* Tooltip */}
            {selSpot && (() => {
              const h = hotspots.find((x) => x.id===selSpot)!;
              return (
                <div className="absolute bg-white rounded-xl shadow-xl border border-slate-200 p-4 w-56 z-20"
                  style={{ left:`${Math.min(h.x+4,58)}%`, top:`${Math.min(h.y-5,60)}%` }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-slate-800 text-sm">{h.label}</span>
                    <button onClick={() => setSelSpot(null)} className="text-slate-300 hover:text-slate-600"><X className="w-3.5 h-3.5" /></button>
                  </div>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="text-center"><div className="text-xl font-black font-mono text-slate-800">{h.r}</div><div className="text-[9px] text-slate-400">reports</div></div>
                    <div className="text-center"><div className={`text-xl font-black font-mono ${h.risk==="HIGH"?"text-red-600":"text-amber-600"}`}>{h.sif}</div><div className="text-[9px] text-slate-400">SIF</div></div>
                    <RiskPill level={h.risk} />
                  </div>
                  <div className="text-[11px] text-slate-500 border-t border-slate-100 pt-2">
                    <span className="font-bold text-slate-600">Top precursor: </span>{h.p}
                  </div>
                </div>
              );
            })()}

            {/* LIVE badge */}
            <div className="absolute top-3 left-3 flex items-center gap-2 text-[10px] font-bold rounded-full px-2.5 py-1" style={{ background: "rgba(0,201,201,0.12)", border: "1px solid rgba(0,201,201,0.25)", color: "#00c9c9" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE · Duliajan Field
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════ REPORTS ═══════════════════════════ */
function Reports({ onViewReport }: { onViewReport: (r: Report) => void }) {
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<"table"|"cards">("table");
  const filtered = reports.filter((r) => r.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      <div className="px-6 pt-5 pb-4 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Reports</h1>
          <p className="text-slate-400 text-xs mt-0.5">Searchable HSSE observation explorer</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg overflow-hidden border border-slate-200 text-xs bg-white">
            {(["table","cards"] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-3 py-1.5 capitalize transition-colors ${mode===m?"text-white font-semibold":"text-slate-500 hover:bg-slate-50"}`}
                style={mode===m?{background:"#0d5555"}:{}}>
                {m==="table"?"Table":"Cards"}
              </button>
            ))}
          </div>
          <button className="flex items-center gap-1.5 text-xs text-white font-semibold border border-transparent px-3 py-1.5 rounded-lg" style={{ background: "#e86c1a" }}>
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 mb-4 flex flex-wrap gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-300" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by title, site, LSR…"
            className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 bg-white rounded-lg outline-none focus:ring-2 focus:ring-cyan-200/50 w-60" />
        </div>
        {["Date","Site","Activity","LSR","SIF Classification","Confidence","Report Type"].map((f) => (
          <button key={f} className="flex items-center gap-1 text-[11px] text-slate-500 border border-slate-200 bg-white px-2.5 py-1.5 rounded-lg hover:bg-slate-50">
            {f} <ChevronDown className="w-3 h-3" />
          </button>
        ))}
      </div>

      <div className="px-6 pb-6">
        {mode === "table" ? (
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
                  {["Priority","Report","LSR","Site","Type","Confidence","Date","Action"].map((h,i) => (
                    <th key={h} className={`py-2.5 ${i===0?"px-5":"px-4"} ${i===7?"text-right pr-5":""}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id} className="border-b border-slate-50 hover:bg-cyan-50/20 transition-colors cursor-pointer" onClick={() => onViewReport(r)}>
                    <td className="px-5 py-3"><RiskPill level={r.priority} /></td>
                    <td className="px-4 py-3"><div className="font-semibold text-slate-800 text-[13px]">{r.title}</div><div className="text-[10px] font-mono text-slate-400">{r.id}</div></td>
                    <td className="px-4 py-3 text-[11px] font-semibold" style={{ color: "#0d5555" }}>{r.lsr}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">{r.site}</td>
                    <td className="px-4 py-3"><span className="text-[10px] bg-slate-100 text-slate-600 rounded-full px-2 py-0.5 font-medium">{r.reportType}</span></td>
                    <td className="px-4 py-3 w-28"><ConfBar value={r.confidence} /></td>
                    <td className="px-4 py-3 text-[11px] text-slate-400">{r.date}</td>
                    <td className="px-5 py-3 text-right">
                      <button className="flex items-center gap-1 text-xs font-semibold ml-auto px-2.5 py-1 rounded-lg" style={{ color: "#0d5555" }}>
                        View <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {filtered.map((r) => (
              <div key={r.id} className="bg-white border border-slate-100 rounded-xl p-4 shadow-sm hover:shadow-md transition-all cursor-pointer" onClick={() => onViewReport(r)}>
                <div className="flex items-start justify-between mb-2">
                  <RiskPill level={r.priority} /><span className="text-[10px] font-mono text-slate-400">{r.id}</span>
                </div>
                <h3 className="font-bold text-slate-800 text-sm leading-snug mb-2">{r.title}</h3>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  <span className="text-[10px] font-semibold rounded-full px-2 py-0.5" style={{ background:"rgba(0,201,201,0.1)",color:"#0d5555" }}>{r.lsr}</span>
                  <span className="text-[10px] bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">{r.site}</span>
                  <span className="text-[10px] bg-orange-50 text-orange-600 rounded-full px-2 py-0.5">{r.barrierFailure}</span>
                </div>
                <ConfBar value={r.confidence} />
                <button className="mt-3 w-full text-xs font-bold py-1.5 rounded-lg border transition-colors" style={{ color:"#0d5555",background:"rgba(0,201,201,0.07)",borderColor:"rgba(0,201,201,0.15)" }}>
                  View report →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════ NOTIFICATION DRAWER ═══════════════════════════ */
function NotifDrawer({ onClose }: { onClose: () => void }) {
  return (
    <div className="absolute right-0 top-0 h-full w-76 bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col" style={{ width: 300 }}>
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <h2 className="font-bold text-slate-800">Notifications</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {notifications.map((n) => (
          <div key={n.id} className={`rounded-xl border p-4 ${n.level==="HIGH"?"bg-red-50 border-red-100":"bg-amber-50 border-amber-100"}`}>
            <div className="flex items-start gap-2.5">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${n.level==="HIGH"?"bg-red-100":"bg-amber-100"}`}>
                <AlertTriangle className={`w-3.5 h-3.5 ${n.level==="HIGH"?"text-red-600":"text-amber-600"}`} />
              </div>
              <div>
                <div className="font-bold text-slate-800 text-xs mb-0.5">{n.title}</div>
                <p className="text-[11px] text-slate-500 leading-relaxed">{n.body}</p>
                <div className="text-[10px] text-slate-400 mt-1.5">{n.time}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════ ROOT ═══════════════════════════ */
export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [selectedReport, setSelectedReport] = useState<Report|null>(null);
  const [notifOpen, setNotifOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleView = (r: Report) => { setSelectedReport(r); setScreen("report-detail"); };
  const handleBack = () => { setSelectedReport(null); setScreen("reports"); };

  const renderScreen = () => {
    if (screen==="report-detail" && selectedReport) return <ReportDetail report={selectedReport} onBack={handleBack} />;
    switch (screen) {
      case "home":               return <HomePage onNavigate={(s) => { setScreen(s as Screen); setSelectedReport(null); }} />;
      case "sif-triage":         return <SifTriageDashboard />;
      case "risk-dashboard":     return <RiskDashboard />;
      case "precursor-patterns": return <PrecursorPatterns />;
      case "lsr":                return <LifeSavingRules />;
      case "site-intelligence":  return <SiteIntelligence />;
      case "reports":            return <Reports onViewReport={handleView} />;
      case "system":             return <SystemPage />;
      default:                   return <HomePage onNavigate={(s) => { setScreen(s as Screen); setSelectedReport(null); }} />;
    }
  };

  return (
    <div className="h-full flex overflow-hidden" style={{ fontFamily: "'Inter',system-ui,sans-serif", background: "#f0f2f5" }}>
      <Sidebar
        active={screen}
        onNavigate={(s) => { setScreen(s); setSelectedReport(null); }}
        notifOpen={notifOpen}
        setNotifOpen={setNotifOpen}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
      />

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <TopBar screen={screen} reportId={selectedReport?.id} />
        {renderScreen()}
      </main>

      {notifOpen && (
        <div className="absolute inset-0 z-40">
          <div className="absolute inset-0 bg-black/10" onClick={() => setNotifOpen(false)} />
          <NotifDrawer onClose={() => setNotifOpen(false)} />
        </div>
      )}
    </div>
  );
}
