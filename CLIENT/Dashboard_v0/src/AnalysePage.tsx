import { useState } from "react";
import { Zap, AlertTriangle, CheckCircle, Clock, Shield, ChevronDown } from "lucide-react";

/* Loose shape of INFERENCE/pipeline.py analyse() — only what we render. */
type Fact = { value: boolean | "unknown"; span: string | null; source: string };
type Span = { role: string; text: string; start: number; end: number; source: string; score: number };
type Result = {
  report_id: string;
  input: { text: string };
  meta: { language_detected: string; statement_type: string };
  verdict: { label: string; confidence: number; route: string; layers_agreed: string[]; decision_path: string; head_verdict: string | null; head_confidence: number | null };
  eei_facts: Record<string, Fact>;
  energy: { type: string | null; estimate_j: number | null; threshold_j: number | null; formula: string | null; gate: string; inputs: Record<string, unknown> };
  safety_knowledge: { hazard: string | null; barrier: string | null; barrier_failure_mode: string | null; lsr: string[]; potential_consequence: string | null; precursor_cluster: string | null };
  spans: Span[];
  traps_checked: { negation_detected: boolean; negation_scope: string | null; note: string | null };
  uc_ua: { labels: string[]; confidence: number; actor: string | null; basis: string; act_cues: { text: string }[]; condition_cues: { text: string }[] };
  scope: { reject: boolean; p_out_of_scope: number | null; reason: string };
  review: { required: boolean; reason: string | null };
  provenance: { models: Record<string, string | null>; head_predictions: Record<string, { label: unknown; confidence: number }>; processed_at: string };
};

const SAMPLES = [
  "Crane lifting 2 ton pipe over workers, no banksman present, load swung near helper",
  "Monkey board se tool box neeche gira, barricading nahi tha, koi injury nahi hui",
  "Hot work near wellhead without gas test, permit not signed",
  "AC ka remote kharab ho gaya canteen mein",
];

const VERDICT: Record<string, { bg: string; desc: string }> = {
  H_SIF:        { bg: "#991b1b", desc: "Serious injury / fatality occurred" },
  P_SIF:        { bg: "#dc2626", desc: "Energy released with no barrier — nobody hurt this time" },
  L_SIF:        { bg: "#dc2626", desc: "Low-energy SIF event" },
  EXPOSURE:     { bg: "#e86c1a", desc: "Person exposed to high energy, barrier missing or degraded" },
  CAPACITY:     { bg: "#d97706", desc: "Capacity event" },
  LOW_ENERGY:   { bg: "#0d5555", desc: "Energy below SIF threshold" },
  INSUFFICIENT: { bg: "#64748b", desc: "Text does not answer the four questions" },
  NON_EVENT:    { bg: "#16a34a", desc: "No SIF precursor" },
  OUT_OF_SCOPE: { bg: "#94a3b8", desc: "Not a safety observation" },
};

const ROLE_COLOR: Record<string, string> = {
  energy_cue: "#fecaca", exposure_cue: "#fed7aa", control_absent: "#fde68a", control_ineffective: "#fde68a",
  pseudo_control: "#e9d5ff", control_present: "#bbf7d0", negation_cue: "#e2e8f0", injury_cue: "#fca5a5", release_cue: "#fbcfe8",
};

const nice = (s: string | null | undefined) => (s ? s.replace(/_/g, " ") : "—");

/* Paint spans over the text; overlapping spans keep the first (longest-first) match. */
function Highlighted({ text, spans }: { text: string; spans: Span[] }) {
  const taken: (Span | null)[] = Array(text.length).fill(null);
  [...spans].sort((a, b) => (b.end - b.start) - (a.end - a.start))
    .forEach((s) => { for (let i = s.start; i < s.end && i < text.length; i++) taken[i] ??= s; });
  const parts: { s: Span | null; t: string }[] = [];
  for (let i = 0; i < text.length; i++) {
    const last = parts[parts.length - 1];
    if (last && last.s === taken[i]) last.t += text[i];
    else parts.push({ s: taken[i], t: text[i] });
  }
  return (
    <p className="text-[15px] leading-8 text-slate-800">
      {parts.map((p, i) => p.s
        ? <mark key={i} title={`${p.s.role} · ${p.s.source} · ${p.s.score}`} className="rounded px-0.5" style={{ background: ROLE_COLOR[p.s.role] ?? "#cffafe" }}>{p.t}</mark>
        : <span key={i}>{p.t}</span>)}
    </p>
  );
}

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-100 shadow-sm p-5 ${className}`}>
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">{title}</div>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-slate-50 last:border-0 text-[12.5px]">
      <span className="text-slate-500">{k}</span><span className="font-semibold text-slate-800 text-right">{v}</span>
    </div>
  );
}

export default function AnalysePage() {
  const [text, setText] = useState("");
  const [site, setSite] = useState("");
  const [activity, setActivity] = useState("");
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ms, setMs] = useState(0);

  async function run() {
    if (text.trim().length < 3 || busy) return;
    setBusy(true); setErr(null);
    const t0 = performance.now();
    try {
      const r = await fetch("/api/analyse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, meta: { site: site || null, activity: activity || null } }),
      });
      const body = await r.json().catch(() => null);
      if (!r.ok) throw new Error(body?.detail ? JSON.stringify(body.detail) : `HTTP ${r.status}`);
      setRes(body); setMs(Math.round(performance.now() - t0));
    } catch (e) {
      setErr(`${(e as Error).message} — is the backend running on :8000?`);
    } finally {
      setBusy(false);
    }
  }

  const v = res && (VERDICT[res.verdict.label] ?? { bg: "#0d5555", desc: "" });

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: "#f0f2f5" }}>
      <div className="px-6 pt-5 pb-3">
        <h1 className="text-xl font-bold text-slate-800">Analyse a Statement</h1>
        <p className="text-slate-400 text-xs mt-0.5">Paste an observation / near-miss report (English, Hindi, Hinglish) — the local model returns verdict, evidence and safety knowledge.</p>
      </div>

      {/* ── Input ── */}
      <div className="px-6">
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run(); }}
            rows={4}
            placeholder="e.g. Monkey board se tool box neeche gira, barricading nahi tha…"
            className="w-full resize-y border border-slate-200 rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-300"
          />
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <input value={site} onChange={(e) => setSite(e.target.value)} placeholder="Site (optional)" className="border border-slate-200 rounded-md px-2.5 py-1.5 text-[12px] w-40 focus:outline-none" />
            <input value={activity} onChange={(e) => setActivity(e.target.value)} placeholder="Activity (optional)" className="border border-slate-200 rounded-md px-2.5 py-1.5 text-[12px] w-40 focus:outline-none" />
            <span className="text-[11px] text-slate-400 ml-2">Try:</span>
            {SAMPLES.map((s) => (
              <button key={s} onClick={() => setText(s)} className="text-[11px] rounded-full px-2.5 py-1 max-w-56 truncate hover:opacity-80" style={{ background: "rgba(0,201,201,0.1)", color: "#0d5555" }} title={s}>{s}</button>
            ))}
            <button onClick={run} disabled={busy || text.trim().length < 3}
              className="ml-auto flex items-center gap-1.5 text-white text-xs font-bold px-5 py-2 rounded-lg disabled:opacity-40" style={{ background: "#0d5555" }}>
              <Zap className="w-3.5 h-3.5" /> {busy ? "Analysing…" : "Analyse"} <span className="opacity-50 font-normal">Ctrl+↵</span>
            </button>
          </div>
          {err && <div className="mt-3 text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{err}</div>}
        </div>
      </div>

      {res && v && (
        <div className="px-6 py-4 space-y-4">
          {/* ── Verdict ── */}
          <div className="rounded-xl p-5 text-white shadow-sm flex flex-wrap items-center gap-6" style={{ background: v.bg }}>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest opacity-70">Verdict</div>
              <div className="text-3xl font-black tracking-tight">{nice(res.verdict.label)}</div>
              <div className="text-xs opacity-80">{v.desc}</div>
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest opacity-70">Confidence</div>
              <div className="text-3xl font-black font-mono">{Math.round(res.verdict.confidence * 100)}%</div>
            </div>
            <div className="text-xs opacity-90 space-y-0.5">
              <div>Route: <b>{res.verdict.route}</b></div>
              <div>Layers agreed: <b>{res.verdict.layers_agreed.join(", ") || "—"}</b></div>
              <div>Language: <b>{res.meta.language_detected}</b> · {nice(res.meta.statement_type)}</div>
            </div>
            <div className="ml-auto flex flex-col items-end gap-2">
              {res.review.required
                ? <span className="flex items-center gap-1.5 text-[11px] font-semibold bg-white/15 rounded-lg px-3 py-1.5"><Clock className="w-3.5 h-3.5" /> Human review: {res.review.reason}</span>
                : <span className="flex items-center gap-1.5 text-[11px] font-semibold bg-white/15 rounded-lg px-3 py-1.5"><CheckCircle className="w-3.5 h-3.5" /> No review needed</span>}
              <span className="text-[10px] font-mono opacity-60">{res.report_id} · {ms} ms</span>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-100 shadow-sm px-5 py-3 text-[12px] font-mono text-slate-600">
            <span className="font-sans font-bold text-[10px] uppercase tracking-widest text-slate-400 mr-2">Decision path</span>{res.verdict.decision_path}
          </div>

          {res.traps_checked.negation_detected && res.traps_checked.note && (
            <div className="flex items-start gap-2 rounded-xl px-4 py-3 bg-amber-50 border border-amber-200 text-[12.5px] text-amber-800">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span><b>Negation ({res.traps_checked.negation_scope}):</b> {res.traps_checked.note}</span>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            {/* Evidence */}
            <Card title="Evidence in text" className="col-span-2">
              <Highlighted text={res.input.text} spans={res.spans} />
              <div className="flex flex-wrap gap-1.5 mt-4 pt-3 border-t border-slate-100">
                {res.spans.map((s, i) => (
                  <span key={i} className="text-[10.5px] rounded-md px-2 py-0.5 text-slate-700" style={{ background: ROLE_COLOR[s.role] ?? "#cffafe" }}>
                    <b>{nice(s.role)}</b>: {s.text} <span className="opacity-50">({s.source}{s.source !== "rules" ? ` ${s.score}` : ""})</span>
                  </span>
                ))}
              </div>
            </Card>

            {/* Four questions */}
            <Card title="The four questions (EEI)">
              {Object.entries(res.eei_facts).map(([k, f]) => (
                <div key={k} className="py-2 border-b border-slate-50 last:border-0">
                  <div className="flex justify-between text-[12.5px]">
                    <span className="text-slate-600">{nice(k)}</span>
                    <span className={`font-bold ${f.value === true ? "text-red-600" : f.value === false ? "text-emerald-600" : "text-slate-400"}`}>{String(f.value)}</span>
                  </div>
                  <div className="text-[10.5px] text-slate-400">{f.span ? `“${f.span}” · ` : ""}{f.source}</div>
                </div>
              ))}
            </Card>

            {/* Safety knowledge */}
            <Card title="Safety knowledge">
              <Row k="Hazard" v={nice(res.safety_knowledge.hazard)} />
              <Row k="Required barrier" v={nice(res.safety_knowledge.barrier)} />
              <Row k="Barrier failure" v={nice(res.safety_knowledge.barrier_failure_mode)} />
              <Row k="Potential consequence" v={nice(res.safety_knowledge.potential_consequence)} />
              <Row k="Precursor cluster" v={<span className="font-mono text-[11px]">{res.safety_knowledge.precursor_cluster ?? "—"}</span>} />
              <div className="flex flex-wrap gap-1.5 mt-3">
                {res.safety_knowledge.lsr.length
                  ? res.safety_knowledge.lsr.map((l) => (
                    <span key={l} className="flex items-center gap-1 text-[11px] font-semibold rounded-full px-2.5 py-1" style={{ background: "rgba(0,201,201,0.1)", color: "#0d5555" }}>
                      <Shield className="w-3 h-3" /> {nice(l)}
                    </span>))
                  : <span className="text-[11px] text-slate-400">No Life-Saving Rule mapped</span>}
              </div>
            </Card>

            {/* Energy */}
            <Card title="Energy">
              <Row k="Type" v={nice(res.energy.type)} />
              <Row k="Estimate" v={res.energy.estimate_j != null ? `${res.energy.estimate_j} J` : "—"} />
              <Row k="SIF threshold" v={res.energy.threshold_j != null ? `${res.energy.threshold_j} J` : "—"} />
              <Row k="Gate" v={<span className={res.energy.gate === "EXCEEDS" ? "text-red-600" : ""}>{res.energy.gate}</span>} />
              {res.energy.formula && <div className="mt-2 text-[11px] font-mono text-slate-500">{res.energy.formula}</div>}
            </Card>

            {/* UC / UA */}
            <Card title="Unsafe act / unsafe condition">
              <div className="flex gap-2 mb-3">
                {res.uc_ua.labels.length
                  ? res.uc_ua.labels.map((l) => <span key={l} className="text-xs font-bold px-3 py-1 rounded-lg text-white" style={{ background: l === "UA" ? "#e86c1a" : "#2563eb" }}>{l === "UA" ? "Unsafe Act" : l === "UC" ? "Unsafe Condition" : l}</span>)
                  : <span className="text-[11px] text-slate-400">None detected</span>}
              </div>
              <Row k="Confidence" v={`${Math.round(res.uc_ua.confidence * 100)}%`} />
              <Row k="Actor" v={res.uc_ua.actor ?? "—"} />
              <Row k="Act cues" v={res.uc_ua.act_cues.map((c) => c.text).join(", ") || "—"} />
              <Row k="Condition cues" v={res.uc_ua.condition_cues.map((c) => c.text).join(", ") || "—"} />
            </Card>

            {/* Models / scope */}
            <Card title="Models & scope" className="col-span-3">
              <div className="grid grid-cols-3 gap-x-10">
                <div>
                  {Object.entries(res.provenance.models).map(([k, m]) => <Row key={k} k={k} v={<span className="font-mono text-[11px]">{m ?? "off"}</span>} />)}
                </div>
                <div>
                  {Object.entries(res.provenance.head_predictions).map(([k, h]) => (
                    <Row key={k} k={`head · ${k}`} v={`${Array.isArray(h.label) ? h.label.join(", ") : String(h.label)} (${Math.round(h.confidence * 100)}%)`} />
                  ))}
                  {!Object.keys(res.provenance.head_predictions).length && <Row k="Sentence heads" v="not loaded" />}
                </div>
                <div>
                  <Row k="Out-of-scope p" v={res.scope.p_out_of_scope != null ? res.scope.p_out_of_scope.toFixed(3) : "—"} />
                  <Row k="Scope reason" v={res.scope.reason} />
                  <Row k="Processed" v={res.provenance.processed_at} />
                </div>
              </div>
            </Card>
          </div>

          <details className="bg-white rounded-xl border border-slate-100 shadow-sm group">
            <summary className="px-5 py-3 cursor-pointer text-[12px] font-bold text-slate-600 flex items-center gap-1.5">
              <ChevronDown className="w-3.5 h-3.5 group-open:rotate-180 transition-transform" /> Raw JSON
            </summary>
            <pre className="px-5 pb-4 text-[11px] font-mono text-slate-600 overflow-auto max-h-96">{JSON.stringify(res, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
