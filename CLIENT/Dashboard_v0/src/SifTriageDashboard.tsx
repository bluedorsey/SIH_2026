import { useState } from "react";
import {
  ChevronDown, X, AlertTriangle, CheckCircle, Flag,
  RefreshCw, Sun, Upload, Activity,
} from "lucide-react";

/* ─── DATA ─── */
const SITES = ["Duliajan","Moran","Naharkatiya","Jorhat","Baghjan","Rajasthan (Jodhpur)","KG Basin"];
const RULES = ["LF","EI","CS","WH","HW","DR","BY","FD","PW"];
const RULE_FULL: Record<string,string> = {
  LF:"Line of Fire", EI:"Energy Isolation", CS:"Confined Space",
  WH:"Working at Height", HW:"Hot Work", DR:"Driving", BY:"Bypass",
  FD:"Fatigue / Driving", PW:"Pressure / Well Control",
};

const HEATMAP: number[][] = [
  [7,3,0,4,1,2,1,0,2],
  [4,6,1,2,5,1,3,1,4],
  [5,2,0,3,0,6,0,1,1],
  [1,1,0,1,2,1,0,2,1],
  [2,8,3,1,2,0,4,0,5],
  [1,2,4,0,1,3,1,1,2],
  [3,1,2,6,0,1,2,0,1],
];

const ACT_FIRST = [
  { id:"OIL-2026-0914", desc:"Rig floor par tong ka 8 kg counterweight monkey board se gir gaya — worker standing 1.5 m from drop zone", site:"Duliajan", age:"4 hours ago" },
  { id:"OIL-2026-0908", desc:"Gas line-ot pressure thakiley bhi LOTO tag nai asil, valve khulise — energy not isolated before valve work", site:"Baghjan", age:"6 hours ago" },
  { id:"OIL-2026-0902", desc:"Elevator link parted at 6 m and fell to the rig floor; derrickman had just stepped away from the impact zone", site:"Naharkatiya", age:"3 days ago" },
];

type Verdict = "P-SIF" | "Exposure" | "Insufficient" | "Non-Event" | "Unclassified";
interface ReportRow {
  id: string; verdict: Verdict; site: string; date: string; energy: string;
  rule: string; barrier: string; reviewer: string; lang: string; review: string;
  desc: string; sourceType: string; role: string; activity: string; langConf: string;
}
const REPORT_ROWS: ReportRow[] = [
  { id:"OIL-2026-0914", verdict:"P-SIF",        site:"Duliajan",         date:"09 Sep", energy:"1,570 J", rule:"LF",    barrier:"absent",     reviewer:"HG", lang:"HI",  review:"unreviewed", desc:"Rig floor par tong ka 8 kg counterweight monkey board se gir gaya — worker standing 1.5 m", sourceType:"Near-miss",    role:"Assistant Driller", activity:"Workover rig",  langConf:"Hinglish · 0.94" },
  { id:"OIL-2026-0911", verdict:"Exposure",      site:"Moran",            date:"09 Sep", energy:"2,400 J", rule:"HW PW", barrier:"absent",     reviewer:"HI", lang:"EN",  review:"unreviewed", desc:"Hot work permit issued but gas detector not calibrated — flare source present within 15 m",  sourceType:"Unsafe Act",   role:"HSE Officer",       activity:"Hot Work",      langConf:"English · 0.98" },
  { id:"OIL-2026-0908", verdict:"P-SIF",        site:"Baghjan",          date:"09 Sep", energy:"–",       rule:"EI",    barrier:"unknown",    reviewer:"AS", lang:"AS",  review:"unreviewed", desc:"Gas line-ot pressure thakiley bhi LOTO tag nai asil, valve khulise",                         sourceType:"Near-miss",    role:"Shift Supervisor",  activity:"Maintenance",   langConf:"Assamese · 0.87" },
  { id:"OIL-2026-0905", verdict:"Insufficient",  site:"Jorhat",           date:"08 Sep", energy:"unknown", rule:"–",     barrier:"unknown",    reviewer:"HG", lang:"HI",  review:"needs info", desc:"Some activity near wellhead — details unclear from report text, follow up required",          sourceType:"Unsafe Cond.", role:"Field Operator",    activity:"Wellhead Ops",  langConf:"Hindi · 0.61" },
  { id:"OIL-2026-0902", verdict:"P-SIF",        site:"Naharkatiya",      date:"08 Sep", energy:"8,400 J", rule:"LF WH", barrier:"ineffective",reviewer:"EN", lang:"EN",  review:"unreviewed", desc:"Elevator link parted at 6 m and fell to the rig floor; derrickman had just stepped away",    sourceType:"Near-miss",    role:"Derrickman",        activity:"Workover rig",  langConf:"English · 0.97" },
  { id:"OIL-2026-0899", verdict:"Non-Event",     site:"Duliajan",         date:"08 Sep", energy:"low",     rule:"PPE",   barrier:"present",    reviewer:"HG", lang:"HI",  review:"reviewed",   desc:"Safety boots not worn during routine yard inspection — no immediate hazard exposure",          sourceType:"Unsafe Act",   role:"Supervisor",        activity:"Inspection",    langConf:"Hindi · 0.92" },
  { id:"OIL-2026-0895", verdict:"Exposure",      site:"KG Basin",         date:"07 Sep", energy:"3,100 J", rule:"CS",    barrier:"marginal",   reviewer:"AS", lang:"EN",  review:"unreviewed", desc:"Vessel entry commenced before atmospheric test completion — H2S sensor present but unchecked", sourceType:"Near-miss",    role:"Process Operator",  activity:"Confined Space","langConf":"English · 0.95" },
  { id:"OIL-2026-0891", verdict:"Unclassified",  site:"Rajasthan (Jodhpur)", date:"07 Sep", energy:"–",   rule:"DR",    barrier:"unknown",    reviewer:"HG", lang:"HI",  review:"pending",    desc:"Vehicle incident on site road — narrative incomplete, reporter not reachable",                 sourceType:"Incident",     role:"Driver",            activity:"Driving",       langConf:"Hindi · 0.55" },
];

/* ─── HELPERS ─── */
function heatColor(v: number): React.CSSProperties {
  if (v === 0) return { background: "transparent", color: "#94a3b8" };
  if (v >= 8) return { background: "#2f5fb3", color: "#fff", fontWeight: 700 };
  if (v >= 6) return { background: "#5c87cd", color: "#fff" };
  if (v >= 4) return { background: "#8fb0e0", color: "#1a2233" };
  if (v >= 3) return { background: "#b9cdec", color: "#1a2233" };
  return { background: "#dfe8f5", color: "#1a2233" };
}

type VerdictStyle = { bg: string; text: string; label: string; dot?: string };
const VERDICT: Record<Verdict, VerdictStyle> = {
  "P-SIF":        { bg: "#fdf1f0", text: "#c0362c", label: "■ P-SIF",       dot: "#c0362c" },
  "Exposure":     { bg: "#fdf4e8", text: "#c9822a", label: "□ Exposure",     dot: "#c9822a" },
  "Insufficient": { bg: "#eef1f7", text: "#5c6b8a", label: "? Insufficient", dot: "#8a93a3" },
  "Non-Event":    { bg: "#edfaf3", text: "#2f7a4f", label: "✓ Non-Event",    dot: "#2f7a4f" },
  "Unclassified": { bg: "#f4f5f7", text: "#8a93a3", label: "· Unclassified", dot: "#c7cdd8" },
};

function VTag({ verdict }: { verdict: Verdict }) {
  const s = VERDICT[verdict];
  return (
    <span className="inline-block text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: s.bg, color: s.text }}>
      {s.label}
    </span>
  );
}

function Dot3() {
  return <span className="inline-flex gap-0.5 items-center">{[0,1,2].map((i) => <span key={i} className="w-1.5 h-1.5 rounded-full bg-slate-400" />)}</span>;
}

function SelectCtl({ label, options }: { label: string; options: string[] }) {
  return (
    <select className="border border-slate-200 bg-white rounded-md px-2.5 py-1.5 text-[12px] text-slate-700 focus:outline-none focus:ring-1 cursor-pointer" style={{ minWidth: 110 }}>
      <option>{label}</option>
      {options.map((o) => <option key={o}>{o}</option>)}
    </select>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN DASHBOARD
═══════════════════════════════════════════════════════ */
export default function SifTriageDashboard() {
  const [selReport, setSelReport] = useState<ReportRow>(REPORT_ROWS[0]);
  const [checked, setChecked] = useState<Set<string>>(new Set(["OIL-2026-0914"]));
  const [activeTab, setActiveTab] = useState<"All"|"Uncertain"|"Disagreements"|"Language">("All");
  const [hoverRule, setHoverRule] = useState<string | null>(null);
  const [chips, setChips] = useState(["This week", "Review: unreviewed"]);

  const toggle = (id: string) => {
    const next = new Set(checked);
    next.has(id) ? next.delete(id) : next.add(id);
    setChecked(next);
  };

  const removeChip = (c: string) => setChips((p) => p.filter((x) => x !== c));

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#f7f8fa]" style={{ fontFamily: "'Inter',system-ui,sans-serif", fontSize: 14 }}>

      {/* ── TOP BAR ── */}
      <header className="flex items-center gap-3 px-5 py-2.5 bg-white border-b border-slate-200 flex-wrap shrink-0">
        {/* Filters */}
        <SelectCtl label="This week" options={["Last week","Last 30 days","Last 90 days"]} />
        <SelectCtl label="Site 7" options={SITES} />
        <SelectCtl label="Activity: All" options={["Lifting","Confined Space","Hot Work","Driving"]} />
        <SelectCtl label="Rule: All" options={RULES} />
        <SelectCtl label="Verdict: All" options={["P-SIF","Exposure","Insufficient","Non-Event"]} />
        <SelectCtl label="Review: Unreviewed" options={["All","Reviewed","Needs Info","Pending"]} />

        {/* Right cluster */}
        <div className="ml-auto flex items-center gap-4 text-[12px] text-slate-500 flex-wrap">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold" style={{ background: "#fdf1e9", color: "#a15c1f", border: "1px solid #f3d8bc" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> Offline · 06:40 · 3 pending
          </span>
          <button className="flex items-center gap-1 hover:text-slate-700"><Sun className="w-3.5 h-3.5" /> Light</button>
          <span className="text-slate-400">Field</span>
          <button className="flex items-center gap-1 hover:text-slate-700"><Upload className="w-3.5 h-3.5" /> Export</button>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400" /> State: Live</span>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ background: "#2f5fb3" }}>SB</div>
            <span className="font-medium text-slate-700">S. Borgohain</span>
          </div>
        </div>
      </header>

      {/* ── FILTER CHIPS BAR ── */}
      <div className="flex items-center gap-2.5 px-5 py-2 bg-white border-b border-slate-200 text-[12px] text-slate-500 flex-wrap shrink-0">
        <span className="font-semibold text-slate-400 uppercase tracking-widest text-[10px]">Filters</span>
        {chips.map((c) => (
          <span key={c} className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[12px] font-medium" style={{ background: "#dfe8f5", color: "#2c4470" }}>
            {c}
            <button onClick={() => removeChip(c)} className="hover:opacity-70 leading-none text-[13px]">×</button>
          </span>
        ))}
        {chips.length > 0 && (
          <button onClick={() => setChips([])} className="font-semibold" style={{ color: "#2f5fb3" }}>clear all</button>
        )}
        <span className="ml-auto text-slate-400 text-[11px]">All sites → Duliajan → Workover rig → Line of Fire</span>
      </div>

      {/* ── SCROLLABLE BODY ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[1600px] mx-auto px-5 py-4 space-y-3.5">

          {/* ── KPI ROW ── */}
          <div className="grid grid-cols-5 gap-3.5">
            {[
              { sq: "#c0362c", sqBorder: false, label: "P-SIF THIS WEEK",     value: "9",   delta: "▲ 12%", deltaUp: true,  foot: "fatal potential · nothing happened · 6 unreviewed" },
              { sq: "#fff",    sqBorder: true,  label: "EXPOSURE + CAPACITY",  value: "41",  delta: "▼ 4%",  deltaUp: false, foot: "control missing or marginal · 18 unreviewed" },
              { sq: null,                       label: "REPORTS INGESTED",     value: "186", delta: "▲ 12",  deltaUp: true,  foot: "last batch 14:32 today · 47 reports" },
              { sq: null,                       label: "UNCERTAIN LANE",       value: "24",  delta: "▲ 6",   deltaUp: true,  foot: "reader ran on all · 12.9% of intake" },
              { sq: null,                       label: "AWAITING REVIEW",      value: "23",  delta: "▲ 8",   deltaUp: true,  foot: "oldest 3 days · est. 45 min" },
            ].map((k) => (
              <div key={k.label} className="bg-white border border-slate-200 rounded-lg px-4 py-3.5 shadow-sm">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mb-2 font-semibold tracking-wide uppercase">
                  {k.sq !== null && (
                    <span className="w-2 h-2 rounded-[3px] shrink-0 inline-block"
                      style={{ background: k.sq, border: k.sqBorder ? "1px solid #4a5568" : "none" }} />
                  )}
                  {k.label}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-[28px] font-bold leading-none text-slate-800">{k.value}</span>
                  <span className={`text-[12px] font-semibold ${k.deltaUp ? "text-red-600" : "text-emerald-600"}`}>{k.delta}</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{k.foot}</div>
              </div>
            ))}
          </div>

          {/* ── PANELS ROW ── */}
          <div className="grid gap-3.5" style={{ gridTemplateColumns: "1.5fr 1fr 1fr" }}>

            {/* Panel A — Site × Rule Heatmap */}
            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <h3 className="text-[13px] font-bold text-slate-800 mb-3 flex items-baseline gap-2">
                A · Site × Rule
                <span className="font-normal text-[11px] text-slate-400">P-SIF + Exposure · click a cell to filter the queue</span>
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-[12px]" style={{ borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th className="text-left pb-2 pr-2 w-32" />
                      {RULES.map((r) => (
                        <th key={r}
                          onMouseEnter={() => setHoverRule(r)}
                          onMouseLeave={() => setHoverRule(null)}
                          className="text-center pb-2 font-semibold text-slate-500 cursor-pointer relative"
                          title={RULE_FULL[r]}>
                          <span className={`text-[11px] px-0.5 transition-colors ${hoverRule === r ? "text-blue-700 font-bold" : ""}`}>{r}</span>
                        </th>
                      ))}
                    </tr>
                    {hoverRule && (
                      <tr>
                        <td colSpan={RULES.length + 1} className="pb-1">
                          <div className="text-[11px] text-blue-700 font-semibold">{RULE_FULL[hoverRule]}</div>
                        </td>
                      </tr>
                    )}
                  </thead>
                  <tbody>
                    {SITES.map((site, si) => (
                      <tr key={site}>
                        <td className="text-[12px] text-slate-700 pr-3 py-1.5 whitespace-nowrap">{site}</td>
                        {HEATMAP[si].map((v, ci) => (
                          <td key={ci} className="text-center py-1.5 px-1 cursor-pointer rounded"
                            style={{ ...heatColor(v), borderRadius: 4, transition: "opacity .15s" }}
                            onClick={() => {}}
                            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.7")}
                            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}>
                            {v === 0 ? <span className="text-slate-300">-</span> : v}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between mt-3 text-[11px] text-slate-400">
                <div className="flex items-center gap-1">
                  <span>fewer</span>
                  <div className="flex gap-0.5 mx-1">
                    {["#dfe8f5","#b9cdec","#8fb0e0","#5c87cd","#2f5fb3"].map((c) => (
                      <span key={c} className="w-3.5 h-2 rounded-[2px] inline-block" style={{ background: c }} />
                    ))}
                  </div>
                  <span>more</span>
                </div>
                <span className="italic">hover a column for the rule name</span>
              </div>
            </div>

            {/* Panel B — Verdict Mix */}
            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <h3 className="text-[13px] font-bold text-slate-800 mb-4">B · Verdict mix vs last period</h3>
              {[
                { label: "This period", count: "186 reports", bars: [
                  { color: "#c0362c", w: "5%"  },
                  { color: "#c9822a", w: "16%" },
                  { color: "#e3c25a", w: "9%"  },
                  { color: "#2f7a4f", w: "28%" },
                  { color: "#c7cdd8", w: "42%" },
                ]},
                { label: "Last period", count: "174 reports", bars: [
                  { color: "#c0362c", w: "4%"  },
                  { color: "#c9822a", w: "13%" },
                  { color: "#e3c25a", w: "8%"  },
                  { color: "#2f7a4f", w: "36%" },
                  { color: "#c7cdd8", w: "39%" },
                ]},
              ].map((period) => (
                <div key={period.label} className="mb-4">
                  <div className="flex justify-between text-[12px] text-slate-500 mb-1.5">
                    <span>{period.label}</span><span>{period.count}</span>
                  </div>
                  <div className="flex h-3.5 rounded overflow-hidden">
                    {period.bars.map((b, i) => (
                      <div key={i} className="h-full transition-all" style={{ background: b.color, width: b.w }} />
                    ))}
                  </div>
                </div>
              ))}

              {/* Legend */}
              <div className="flex flex-wrap gap-2 mb-4 text-[11px] text-slate-500">
                {[
                  { color: "#c0362c", label: "P-SIF" },
                  { color: "#c9822a", label: "Exposure" },
                  { color: "#e3c25a", label: "Uncertain" },
                  { color: "#2f7a4f", label: "Non-Event" },
                  { color: "#c7cdd8", label: "Unclassified" },
                ].map((l) => (
                  <div key={l.label} className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: l.color }} />
                    {l.label}
                  </div>
                ))}
              </div>

              <div className="text-[13px] text-slate-700 mb-1">
                P-SIF share 4.2% → <strong className="text-red-600">5.1% ▲</strong>
              </div>
              <div className="text-[12px] text-slate-400 italic">The pile is getting worse, not the reporting.</div>
            </div>

            {/* Panel C — Volume Funnel */}
            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <h3 className="text-[13px] font-bold text-slate-800 mb-4">C · Volume funnel · this period</h3>
              {[
                { label: "Ingested",        pct: 100, val: "3,200", color: "#4a5568"  },
                { label: "Fast path",       pct: 87,  val: "2,800", color: "#4a5568"  },
                { label: "Uncertain lane",  pct: 12,  val: "400",   color: "#4a5568"  },
                { label: "P-SIF flagged",   pct: 3,   val: "85",    color: "#c0362c"  },
                { label: "Human reviewed",  pct: 1,   val: "23",    color: "#2f7a4f"  },
                { label: "Overridden",      pct: 0.3, val: "6",     color: "#c7cdd8"  },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-3 mb-2.5">
                  <span className="text-[12px] text-slate-500 w-28 shrink-0">{row.label}</span>
                  <div className="flex-1 h-2.5 rounded-full overflow-hidden" style={{ background: "#eef1f5" }}>
                    <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(row.pct, 0.5)}%`, background: row.color }} />
                  </div>
                  <span className="text-[12px] text-slate-700 font-mono w-12 text-right tabular-nums">{row.val}</span>
                </div>
              ))}
              <div className="mt-3 text-[12px] text-slate-400 italic leading-relaxed">
                6 of 23 reviewed P-SIF were corrected by a human. The loop is real.
              </div>

              {/* Mini annotation */}
              <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
                {[
                  { val: "87%", label: "auto-resolved" },
                  { val: "6.6%", label: "human-reviewed" },
                  { val: "26%", label: "override rate" },
                ].map((s) => (
                  <div key={s.label}>
                    <div className="text-[16px] font-bold text-slate-800">{s.val}</div>
                    <div className="text-[10px] text-slate-400">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── ACT FIRST ── */}
          <div className="rounded-lg p-4 border" style={{ background: "#fdf1f0", borderColor: "#f4d4d0" }}>
            <div className="flex items-baseline gap-2 mb-3 font-bold text-[13.5px]" style={{ color: "#c0362c" }}>
              <AlertTriangle className="w-4 h-4 shrink-0" />
              Unreviewed P-SIF — act first
              <span className="font-normal text-[11.5px]" style={{ color: "#a4574f" }}>oldest 3 days · est. 45 min to clear</span>
            </div>
            <div className="space-y-2">
              {ACT_FIRST.map((a) => (
                <button key={a.id}
                  onClick={() => { const r = REPORT_ROWS.find((x) => x.id === a.id); if (r) setSelReport(r); }}
                  className="w-full flex items-center gap-3 bg-white rounded-lg px-3.5 py-2.5 text-left transition-shadow hover:shadow-md"
                  style={{ border: "1px solid #f4d4d0", borderLeft: "4px solid #c0362c" }}>
                  <span className="text-[10px] font-black px-1.5 py-0.5 rounded text-white shrink-0" style={{ background: "#c0362c" }}>■ P-SIF</span>
                  <span className="font-semibold text-[12.5px] text-slate-500 shrink-0 w-28">{a.id}</span>
                  <span className="flex-1 text-[13px] text-slate-800 truncate">{a.desc}</span>
                  <span className="text-[12.5px] text-slate-500 w-28 shrink-0">{a.site}</span>
                  <span className="text-[12.5px] font-semibold w-24 text-right shrink-0" style={{ color: "#c0362c" }}>{a.age}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ── BOTTOM GRID ── */}
          <div className="grid gap-3.5 pb-4" style={{ gridTemplateColumns: "1.6fr 1fr" }}>

            {/* Reports list */}
            <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
              {/* Tabs */}
              <div className="flex items-center gap-5 px-4 py-3 border-b border-slate-200 text-[12.5px] text-slate-500 flex-wrap">
                {([
                  ["All", "All 186"],
                  ["Uncertain", "Uncertain lane 24"],
                  ["Disagreements", "Disagreements 17"],
                  ["Language", "Language-weak 9"],
                ] as const).map(([id, label]) => (
                  <button key={id} onClick={() => setActiveTab(id)}
                    className={`pb-1 transition-colors ${activeTab === id ? "font-bold text-slate-800 border-b-2 border-blue-600" : "hover:text-slate-700"}`}>
                    {label}
                  </button>
                ))}
                <div className="ml-auto flex items-center gap-2">
                  <span className="text-[12px] text-slate-400">{checked.size} selected</span>
                  <button className="text-[12px] border border-slate-200 bg-slate-50 rounded-md px-2.5 py-1 text-slate-600 hover:bg-slate-100 transition-colors">
                    Agree all Non-Event (14)
                  </button>
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-[12.5px]" style={{ borderCollapse: "collapse" }}>
                  <thead>
                    <tr className="text-[11px] font-semibold text-slate-400 border-b border-slate-200">
                      {["","VERDICT","REPORT ID","SITE","DATE","ENERGY","RULE","BARRIER","AGREE","LANG","REVIEW"].map((h,i) => (
                        <th key={i} className="text-left px-2.5 py-2 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {REPORT_ROWS.map((r) => (
                      <tr key={r.id}
                        onClick={() => setSelReport(r)}
                        className={`border-b border-slate-50 cursor-pointer transition-colors ${selReport.id === r.id ? "bg-blue-50" : "hover:bg-slate-50/60"}`}>
                        <td className="px-2.5 py-2">
                          <input type="checkbox" checked={checked.has(r.id)} onChange={() => toggle(r.id)}
                            onClick={(e) => e.stopPropagation()}
                            className="accent-blue-600 cursor-pointer" />
                        </td>
                        <td className="px-2.5 py-2 whitespace-nowrap"><VTag verdict={r.verdict} /></td>
                        <td className="px-2.5 py-2 font-mono text-slate-600 whitespace-nowrap">{r.id}</td>
                        <td className="px-2.5 py-2 text-slate-600 whitespace-nowrap">{r.site}</td>
                        <td className="px-2.5 py-2 text-slate-500 whitespace-nowrap">{r.date}</td>
                        <td className="px-2.5 py-2 text-slate-500 font-mono whitespace-nowrap text-[11px]">{r.energy}</td>
                        <td className="px-2.5 py-2 font-semibold text-slate-700 whitespace-nowrap">{r.rule}</td>
                        <td className="px-2.5 py-2 text-slate-500 whitespace-nowrap">{r.barrier}</td>
                        <td className="px-2.5 py-2 whitespace-nowrap"><Dot3 /> <span className="text-slate-500 ml-1">{r.reviewer}</span></td>
                        <td className="px-2.5 py-2 text-slate-400 whitespace-nowrap">{r.lang}</td>
                        <td className={`px-2.5 py-2 whitespace-nowrap font-medium text-[11.5px] ${r.review === "reviewed" ? "text-emerald-600" : r.review === "needs info" ? "text-amber-600" : "text-slate-400"}`}>
                          ○ {r.review}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Detail panel */}
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5 font-bold text-[14px] text-slate-800">
                  <span className="font-mono">{selReport.id}</span>
                  <VTag verdict={selReport.verdict} />
                </div>
                <button className="flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-md text-white transition-opacity hover:opacity-80" style={{ background: "#c0362c" }}>
                  <Flag className="w-3 h-3" /> FLAG
                </button>
              </div>

              {/* Metadata grid */}
              <div className="grid grid-cols-3 gap-x-4 gap-y-3 mb-4">
                {[
                  ["Site",          selReport.site],
                  ["Date · time",   `${selReport.date} 2026 · 02:40`],
                  ["Source type",   selReport.sourceType],
                  ["Reporter role", selReport.role],
                  ["Activity",      selReport.activity],
                  ["Language",      selReport.langConf],
                ].map(([k,v]) => (
                  <div key={k}>
                    <div className="text-[10.5px] text-slate-400 mb-0.5 font-medium uppercase tracking-wide">{k}</div>
                    <div className="text-[13px] font-semibold text-slate-800">{v}</div>
                  </div>
                ))}
              </div>

              {/* Description */}
              <div className="bg-slate-50 rounded-lg px-4 py-3 mb-4 border border-slate-100">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">Report text</div>
                <p className="text-[13px] text-slate-700 leading-relaxed">{selReport.desc}</p>
              </div>

              {/* AI classification summary */}
              <div className="border-t border-slate-100 pt-3 text-[12px] text-slate-500 space-y-1 leading-relaxed">
                <div className="flex items-center gap-1.5">
                  <Activity className="w-3 h-3 text-slate-400" />
                  Classified 2.1 s ago · rule engine v4.2
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 flex items-center justify-center">○</span>
                  {selReport.review === "reviewed"
                    ? <span className="text-emerald-600 font-semibold">Reviewed ✓</span>
                    : <span>Not yet reviewed · in queue <strong className="text-slate-700">4 h 12 m</strong></span>}
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-4 flex flex-wrap gap-2">
                <button className="text-[12px] font-bold px-3 py-1.5 rounded-md text-white" style={{ background: "#c0362c" }}>Confirm P-SIF</button>
                <button className="text-[12px] font-semibold px-3 py-1.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50">Mark Non-SIF</button>
                <button className="text-[12px] font-semibold px-3 py-1.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50">Request Info</button>
                <button className="text-[12px] font-semibold px-3 py-1.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50">Add Note</button>
              </div>

              {/* Energy indicator */}
              {selReport.energy !== "–" && selReport.energy !== "unknown" && selReport.energy !== "low" && (
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Detected energy level</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "#eef1f5" }}>
                      <div className="h-full rounded-full" style={{
                        width: selReport.energy === "8,400 J" ? "90%" : selReport.energy === "3,100 J" ? "65%" : selReport.energy === "2,400 J" ? "55%" : selReport.energy === "1,570 J" ? "40%" : "15%",
                        background: "linear-gradient(90deg,#d97706,#c0362c)",
                      }} />
                    </div>
                    <span className="text-[12px] font-mono font-bold text-slate-700">{selReport.energy}</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">Extracted from report · not measured</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
