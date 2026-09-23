import React, { useState, useEffect } from 'react';
import { 
  FileText, Search, Filter, CheckCircle2, Clock, 
  BarChart2, ShieldAlert, AlertTriangle, AlertCircle, 
  HelpCircle, CheckCircle, Info, Zap, Layers, MapPin, Loader2, Calendar, FileCheck, Sparkles, ChevronRight
} from 'lucide-react';
import { getReports, getReportDetail } from '../../services/api';

export default function ReportsView() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  
  const [reportsList, setReportsList] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState('');

  useEffect(() => {
    async function loadReports() {
      try {
        setLoadingList(true);
        const data = await getReports(1, 50);
        const reportsData = data?.data || [];
        setReportsList(reportsData);
        if (reportsData.length > 0) {
          setSelectedReportId(reportsData[0].report_id);
        }
      } catch (err) {
        console.error("Failed to load reports", err);
      } finally {
        setLoadingList(false);
      }
    }
    loadReports();
  }, []);

  useEffect(() => {
    async function loadDetail() {
      if (!selectedReportId) {
        setReportDetail(null);
        return;
      }
      try {
        setLoadingDetail(true);
        setDetailError('');
        const detail = await getReportDetail(selectedReportId);
        setReportDetail(detail);
      } catch (err) {
        console.error("Failed to load report detail", err);
        setDetailError('Failed to load report details.');
      } finally {
        setLoadingDetail(false);
      }
    }
    loadDetail();
  }, [selectedReportId]);

  const filteredReports = reportsList.filter((report) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = 
      (report.report_id || '').toLowerCase().includes(term) ||
      (report.site_code || '').toLowerCase().includes(term);
    return matchesSearch;
  });

  const getFormatBadgeStyle = (format) => {
    switch (format) {
      case 'PDF':
        return 'bg-rose-50 text-rose-700 border-rose-200/80 group-hover:bg-rose-100/80';
      case 'XLSX':
      case 'Excel (.xlsx)':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200/80 group-hover:bg-emerald-100/80';
      case 'CSV':
        return 'bg-sky-50 text-sky-700 border-sky-200/80 group-hover:bg-sky-100/80';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getVerdictBadge = (v) => {
    const text = String(v || "").toUpperCase();
    if (text === "NON_EVENT") return "bg-[#10a37f] text-white";
    if (text === "INSUFFICIENT" || text === "OUT_OF_SCOPE") return "bg-slate-500 text-white";
    if (text === "L_SIF") return "bg-rose-600 text-white";
    if (text === "LOW_ENERGY") return "bg-teal-800 text-white";
    if (text === "H_SIF") return "bg-red-700 text-white";
    if (text === "CAPACITY") return "bg-orange-500 text-white";
    if (text === "P_SIF") return "bg-red-600 text-white";
    if (text === "SUCCESS") return "bg-teal-600 text-white";
    if (text === "EXPOSURE") return "bg-amber-600 text-white";
    
    // Fallbacks
    if (text.includes("HIGH") || text.includes("H_SIF")) return "bg-red-700 text-white";
    if (text.includes("MEDIUM") || text.includes("P_SIF") || text.includes("CAPACITY")) return "bg-orange-500 text-white";
    if (text.includes("LOW") || text.includes("L_SIF")) return "bg-rose-600 text-white";
    if (text.includes("EXPOSURE")) return "bg-amber-600 text-white";
    return "bg-slate-500 text-white";
  };

  return (
    <div className="p-4 sm:p-6 space-y-6 bg-[#f8fafc] min-h-screen text-slate-800">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-linear-to-r from-[#012b28] via-[#013531] to-[#044e47] p-6 text-white shadow-md">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-64 h-64 bg-teal-400/10 rounded-full blur-2xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-200 text-[11px] font-semibold border border-emerald-400/20">
              <Sparkles size={12} />
              Automated Intelligence
            </span>
            <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
              Reports & Executive Intelligence
            </h1>
            <p className="text-xs text-emerald-100/80 max-w-2xl leading-relaxed">
              Explore safety compliance summaries, SIF precursor metrics, and site risk logs.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Pane - List */}
        <div className="lg:col-span-7 xl:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-xs flex flex-col h-[800px]">
          <div className="p-4 border-b border-slate-100 space-y-3">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <BarChart2 size={16} className="text-teal-700" />
              Report Registry
            </h2>
            <div className="flex justify-between items-center relative">
              <div className="relative w-full max-w-xs">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search reports..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-600 focus:border-teal-600 transition-all"
                />
              </div>
              <button 
                onClick={() => {
                  const headers = ['Incident ID', 'Incident', 'Verdict', 'Date', 'Site', 'Location', 'LSR'];
                  const rows = filteredReports.map(r => [
                    r.report_id,
                    `Incident Report - ${r.site_code || 'Unknown'}`,
                    r.verdict || 'Unknown',
                    new Date(r.ingested_at).toLocaleDateString(),
                    r.site_code || 'Unknown',
                    'N/A', // Location not in list API
                    r.lsr_primary || 'N/A'
                  ]);
                  const csvContent = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
                  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                  const link = document.createElement('a');
                  link.href = URL.createObjectURL(blob);
                  link.setAttribute('download', 'reports_export.csv');
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-200 hover:bg-teal-100 rounded-lg transition-colors"
              >
                <FileText size={14} /> Export CSV
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto overflow-x-auto">
            {loadingList ? (
              <div className="flex flex-col items-center justify-center h-40 text-slate-500 space-y-2">
                <Loader2 size={24} className="animate-spin" />
                <span className="text-xs font-semibold">Loading reports...</span>
              </div>
            ) : filteredReports.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-slate-500 space-y-2">
                <FileText size={24} className="text-slate-300" />
                <span className="text-xs font-semibold">No reports found</span>
              </div>
            ) : (
              <table className="w-full text-left text-xs whitespace-nowrap">
                <thead className="bg-slate-50 border-b border-slate-200 sticky top-0 text-slate-500 font-bold tracking-wider">
                  <tr>
                    <th className="p-3">Incident ID</th>
                    <th className="p-3">Incident</th>
                    <th className="p-3">Verdict</th>
                    <th className="p-3">Date</th>
                    <th className="p-3">Site</th>
                    <th className="p-3">Location</th>
                    <th className="p-3">LSR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredReports.map((report) => {
                    const isSelected = selectedReportId === report.report_id;
                    
                    // Row bg logic based on verdict
                    const text = String(report.verdict || "").toUpperCase();
                    let rowBg = "hover:bg-slate-50";
                    if (text === "NON_EVENT") rowBg = "bg-[#10a37f]/10 hover:bg-[#10a37f]/20";
                    else if (text === "INSUFFICIENT" || text === "OUT_OF_SCOPE") rowBg = "bg-slate-500/10 hover:bg-slate-500/20";
                    else if (text === "L_SIF" || text === "P_SIF" || text.includes("HIGH") || text.includes("H_SIF")) rowBg = "bg-red-600/10 hover:bg-red-600/20";
                    else if (text === "LOW_ENERGY" || text === "SUCCESS") rowBg = "bg-teal-600/10 hover:bg-teal-600/20";
                    else if (text === "CAPACITY" || text === "EXPOSURE" || text.includes("MEDIUM")) rowBg = "bg-orange-500/10 hover:bg-orange-500/20";

                    return (
                      <tr 
                        key={report.report_id}
                        onClick={() => setSelectedReportId(report.report_id)}
                        className={`cursor-pointer transition-colors ${rowBg} ${isSelected ? 'border-l-4 border-l-teal-600 shadow-inner' : 'border-l-4 border-l-transparent'}`}
                      >
                        <td className="p-3 font-mono font-semibold text-[10px] text-slate-600 truncate max-w-[100px]" title={report.report_id}>{report.report_id}</td>
                        <td className="p-3 font-semibold text-slate-800">Incident Report - {report.site_code || 'Unknown'}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${getVerdictBadge(report.verdict)}`}>
                            {report.verdict}
                          </span>
                        </td>
                        <td className="p-3 text-slate-600 font-mono">{new Date(report.ingested_at).toLocaleDateString()}</td>
                        <td className="p-3 text-slate-700">{report.site_code || 'Unknown'}</td>
                        <td className="p-3 text-slate-400 italic">N/A</td>
                        <td className="p-3 font-semibold text-slate-700 truncate max-w-[120px]" title={report.lsr_primary}>{report.lsr_primary || 'No LSR'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Pane - Details */}
        <div className="lg:col-span-5 xl:col-span-5 bg-white rounded-xl border border-slate-200/80 shadow-xs h-[800px] overflow-y-auto p-5 sm:p-6">
          {loadingDetail ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3">
              <Loader2 size={32} className="animate-spin text-teal-600" />
              <span className="text-sm font-semibold">Loading report details...</span>
            </div>
          ) : detailError ? (
            <div className="flex flex-col items-center justify-center h-full text-red-500 space-y-3">
              <AlertCircle size={32} />
              <span className="text-sm font-semibold">{detailError}</span>
            </div>
          ) : reportDetail ? (
            <ReportDetailView data={reportDetail} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-3">
              <FileText size={48} className="opacity-20" />
              <span className="text-sm font-semibold">Select a report from the list to view details</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportDetailView({ data }) {
  const { report, verdict, spans } = data;
  const rawText = report?.raw_text || "";
  const v = verdict?.verdict || "UNKNOWN";
  const confidence = verdict?.confidence ? (verdict.confidence * 100).toFixed(0) + "%" : "N/A";
  const fullOutput = verdict?.full_output || {};
  const eei = fullOutput?.eei_facts || {};
  const safetyKnowledge = fullOutput?.safety_knowledge || {};
  const energy = fullOutput?.energy || {};
  const verdictDetail = fullOutput?.verdict_detail || {};
  const ingestedAt = report?.metadata?.ingested_at ? new Date(report.metadata.ingested_at).toLocaleString() : "Unknown";

  let bannerClass = "bg-slate-600 text-white";
  let verdictIcon = <HelpCircle size={24} className="text-white" />;
  
  if (["CAPACITY"].includes(v)) {
    bannerClass = "bg-gradient-to-r from-amber-600 to-orange-600 text-white";
    verdictIcon = <AlertTriangle size={24} className="text-white" />;
  } else if (["H_SIF", "P_SIF", "L_SIF", "SIF", "HIGH SIF POTENTIAL"].includes(v)) {
    bannerClass = "bg-gradient-to-r from-red-700 to-red-600 text-white";
    verdictIcon = <ShieldAlert size={24} className="text-white" />;
  } else if (["EXPOSURE"].includes(v)) {
    bannerClass = "bg-gradient-to-r from-yellow-600 to-amber-500 text-white";
    verdictIcon = <AlertCircle size={24} className="text-white" />;
  } else if (["SUCCESS", "NON_EVENT"].includes(v)) {
    bannerClass = "bg-gradient-to-r from-emerald-700 to-green-600 text-white";
    verdictIcon = <CheckCircle size={24} className="text-white" />;
  } else if (["LOW_ENERGY"].includes(v)) {
    bannerClass = "bg-gradient-to-r from-blue-700 to-blue-600 text-white";
    verdictIcon = <Info size={24} className="text-white" />;
  }

  const renderHighlightedText = () => {
    const text = rawText;
    const s = spans || [];
    
    // Convert char_start/char_end to start/end and sort
    const sortedSpans = [...s].map(span => ({
      ...span,
      start: span.char_start,
      end: span.char_end
    })).filter(s => s.start !== undefined && s.end !== undefined).sort((a, b) => a.start - b.start);
    
    if (sortedSpans.length === 0) return <span>{text}</span>;

    const elements = [];
    let lastIndex = 0;

    sortedSpans.forEach((span, idx) => {
      if (span.start > lastIndex) {
        elements.push(<span key={`text-${idx}`}>{text.substring(lastIndex, span.start)}</span>);
      }
      
      let bgClass = "bg-gray-200";
      if (span.role === "energy_cue") bgClass = "bg-orange-200 text-orange-900";
      else if (span.role === "release_cue") bgClass = "bg-pink-200 text-pink-900";
      else if (span.role === "exposure_cue") bgClass = "bg-purple-200 text-purple-900";
      else if (span.role === "control_present") bgClass = "bg-green-200 text-green-900";
      else if (span.role === "control_absent") bgClass = "bg-red-200 text-red-900";
      else if (span.role === "control_ineffective") bgClass = "bg-yellow-200 text-yellow-900";
      else if (span.role === "outcome_cue") bgClass = "bg-gray-300 text-gray-900";
      else if (span.role === "negation_cue") bgClass = "bg-slate-300 text-slate-900";

      elements.push(
        <mark key={`span-${idx}`} className={`px-1 rounded font-medium ${bgClass}`} title={span.role}>
          {text.substring(span.start, span.end)}
        </mark>
      );
      lastIndex = span.end;
    });

    if (lastIndex < text.length) {
      elements.push(<span key="text-end">{text.substring(lastIndex)}</span>);
    }

    return elements;
  };
  
  const getSpanColorClass = (role) => {
    if (role === "energy_cue") return "bg-orange-100 text-orange-800 border-orange-200";
    if (role === "release_cue") return "bg-pink-100 text-pink-800 border-pink-200";
    if (role === "exposure_cue") return "bg-purple-100 text-purple-800 border-purple-200";
    if (role === "control_present") return "bg-green-100 text-green-800 border-green-200";
    if (role === "control_absent") return "bg-red-100 text-red-800 border-red-200";
    if (role === "control_ineffective") return "bg-yellow-100 text-yellow-800 border-yellow-200";
    if (role === "outcome_cue") return "bg-gray-200 text-gray-800 border-gray-300";
    if (role === "negation_cue") return "bg-slate-200 text-slate-800 border-slate-300";
    return "bg-gray-100 text-gray-800 border-gray-200";
  };

  return (
    <div className="space-y-6">
      {/* 1. VERDICT BANNER */}
      <div className={`rounded-2xl p-5 sm:p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-md ${bannerClass}`}>
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-sm rounded-full">
            {verdictIcon}
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-80 mb-1">Verdict</p>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight">{v}</h2>
            <p className="text-sm font-medium opacity-90 capitalize">{v.replace(/_/g, ' ').toLowerCase()} event</p>
          </div>
        </div>

        <div className="flex flex-col items-start md:items-center px-0 md:px-6 border-t md:border-t-0 md:border-l md:border-r border-white/20 py-3 md:py-0 w-full md:w-auto">
          <p className="text-xs font-bold uppercase tracking-wider opacity-80 mb-1">Confidence</p>
          <div className="text-2xl sm:text-3xl font-black">{confidence}</div>
          <div className="flex items-center gap-2 mt-1 text-[11px] font-semibold opacity-80">
            <span>Route: {verdictDetail?.route || "Unknown"}</span>
            <span>•</span>
            <span>Layers: {(verdictDetail?.layers_agreed || []).join(", ") || "None"}</span>
          </div>
        </div>

        <div className="flex flex-col gap-2 items-start md:items-end w-full md:w-auto">
          <div className="text-right mt-auto">
            <p className="text-xs font-bold opacity-80">{report?.id || report?.metadata?.report_id}</p>
            <p className="text-[10px] font-medium opacity-70 flex items-center gap-1 mt-0.5 justify-start md:justify-end">
              <Clock size={10} /> {ingestedAt}
            </p>
          </div>
        </div>
      </div>

      {/* 2. DECISION PATH */}
      {verdictDetail?.decision_path && (
        <div className="bg-slate-800 text-slate-200 rounded-lg p-3 font-mono text-[11px] sm:text-xs flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 overflow-hidden">
          <span className="font-bold text-slate-400 shrink-0">DECISION PATH</span>
          <span className="text-slate-500 hidden sm:block shrink-0">|</span>
          <span className="break-words whitespace-normal leading-relaxed w-full">
            {verdictDetail.decision_path.replace(/->/g, '→')}
          </span>
        </div>
      )}

      {/* 3. EVIDENCE IN TEXT + THE FOUR QUESTIONS */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Evidence in Text */}
        <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
            <FileText size={16} className="text-teal-700 shrink-0" />
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wide">Evidence in Text</h3>
          </div>
          
          <div className="flex-1 bg-gray-50 rounded-lg p-4 border border-gray-100 text-sm md:text-base leading-relaxed text-gray-800 mb-4 whitespace-pre-wrap break-words">
            {renderHighlightedText()}
          </div>
          
          <div>
            <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Detected Spans</h4>
            <div className="flex flex-wrap gap-2">
              {(spans || []).map((span, idx) => (
                <div key={idx} className={`text-[11px] px-2 py-1 rounded-md border font-semibold flex items-center gap-1.5 max-w-full ${getSpanColorClass(span.role)}`}>
                  <span className="opacity-75 shrink-0">{span.role.replace(/_/g, ' ')}:</span>
                  <span className="truncate">"{span.text_span || text?.substring(span.char_start, span.char_end)}"</span>
                </div>
              ))}
              {(!spans || spans.length === 0) && (
                <span className="text-xs text-gray-500 italic">No specific spans detected.</span>
              )}
            </div>
          </div>
        </div>

        {/* The Four Questions */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
            <HelpCircle size={16} className="text-teal-700 shrink-0" />
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wide">The Four Questions (EEI)</h3>
          </div>
          
          <div className="space-y-4">
            {[
              { label: "High Energy Present", key: "high_energy_present" },
              { label: "Energy Released", key: "energy_released" },
              { label: "Serious Injury", key: "serious_injury" },
              { label: "Direct Control Present", key: "direct_control_present" }
            ].map((q) => {
              const fact = eei?.[q.key];
              if (!fact) return null;
              
              return (
                <div key={q.key} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <div className="flex flex-wrap justify-between items-center mb-1.5 gap-2">
                    <span className="text-xs font-bold text-gray-700 leading-tight flex-1 min-w-[80px]">{q.label}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded shrink-0 ${fact.value ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                      {fact.value ? 'TRUE' : 'FALSE'}
                    </span>
                  </div>
                  {fact.span && (
                    <div className="text-[11px] text-gray-500 italic flex justify-between items-start sm:items-end mt-2 flex-col sm:flex-row gap-2 sm:gap-1">
                      <span className="line-clamp-2 break-words">"{fact.span}"</span>
                      <span className="text-[9px] uppercase bg-gray-200 px-1.5 py-0.5 rounded sm:ml-2 shrink-0 max-w-full truncate" title={fact.source || 'ai'}>{fact.source || 'ai'}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 4. BOTTOM THREE CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Safety Knowledge */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3 border-b border-gray-100 pb-2">
            <Layers size={15} className="text-teal-700" />
            <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">Safety Knowledge</h3>
          </div>
          <div className="space-y-3 text-xs">
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Hazard</p>
              <p className="font-bold text-gray-900 capitalize">{(safetyKnowledge?.hazard || "Unknown").replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Required Barrier</p>
              <p className="font-bold text-gray-900 capitalize">{(safetyKnowledge?.barrier || "Unknown").replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">LSR / Rules</p>
              <p className="font-bold text-gray-900">{(safetyKnowledge?.lsr || []).join(", ") || "None"}</p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Potential Consequence</p>
              <p className="font-bold text-gray-900 capitalize">{(safetyKnowledge?.potential_consequence || "Unknown").replace(/_/g, ' ')}</p>
            </div>
          </div>
        </div>

        {/* Energy */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3 border-b border-gray-100 pb-2">
            <Zap size={15} className="text-teal-700" />
            <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">Energy</h3>
          </div>
          <div className="space-y-3 text-xs">
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Type</p>
              <p className="font-bold text-gray-900 capitalize">{(energy?.type || "Unknown").replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Estimate (Joules)</p>
              <p className="font-bold text-gray-900">{energy?.estimate_j !== null && energy?.estimate_j !== undefined ? energy.estimate_j.toLocaleString() : "—"}</p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">SIF Threshold (Joules)</p>
              <p className="font-bold text-gray-900">{energy?.threshold_j !== null && energy?.threshold_j !== undefined ? energy.threshold_j.toLocaleString() : "—"}</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}