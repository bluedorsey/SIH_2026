import React, { useState, useEffect } from 'react';
import TriageAnalytics from './triage/TriageAnalytics';
import TriageQueue from './triage/TriageQueue';
import { getQueue, approveVerdict, correctVerdict } from '../../services/api';

export default function SifPrecursorTriageView() {
  const [filters, setFilters] = useState({
    timeRange: 'This week',
    site: 'All',
    activity: 'All',
    rule: 'All',
    verdict: 'All',
    review: 'Unreviewed'
  });

  const [selectedReportId, setSelectedReportId] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchQueueData() {
      try {
        setLoading(true);
        const data = await getQueue(1, 50);
        
        const queueData = data?.data || [];
        const mappedReports = queueData.map(item => ({
          id: item.report_id,
          verdictId: item.verdict_id,
          verdict: (item.verdict || 'Unknown').replace('_', '-'),
          site: item.site_code || 'Unknown',
          date: new Date(item.produced_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }),
          energy: item.energy_detail?.estimate_j ? `${item.energy_detail.estimate_j} J` : '-',
          rule: item.lsr_primary || '-',
          barrier: item.barrier_status || 'unknown',
          role: 'Reporter',
          activity: item.activity || 'General',
          language: 'Auto',
          fullDate: new Date(item.produced_at).toLocaleString(),
          sourceType: 'Observation',
          text: item.raw_text || 'No text available',
          reviewStatus: 'Unreviewed',
          inQueue: 'Just now',
          energyValue: item.energy_detail?.estimate_j || 0
        }));
        
        setReports(mappedReports);
        if (mappedReports.length > 0 && !selectedReportId) {
          setSelectedReportId(mappedReports[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch queue", err);
      } finally {
        setLoading(false);
      }
    }
    
    fetchQueueData();
  }, []);

  // Placeholder heatmap data — no backend analytics endpoint yet
  const heatmapRules = ['LF', 'EI', 'CS', 'WH', 'HW', 'DR', 'BY', 'FD', 'PW'];
  const heatmapSites = [
    { name: 'Duliajan', values: [7, 3, 0, 4, 1, 2, 1, 0, 2] },
    { name: 'Moran', values: [4, 6, 1, 2, 5, 1, 3, 1, 4] },
    { name: 'Naharkatiya', values: [5, 2, 0, 3, 0, 6, 0, 1, 1] },
    { name: 'Jorhat', values: [1, 1, 0, 1, 2, 1, 0, 2, 1] },
    { name: 'Baghjan', values: [2, 8, 3, 1, 2, 0, 4, 0, 5] },
    { name: 'Rajasthan (Jodhpur)', values: [1, 2, 4, 0, 1, 3, 1, 1, 2] },
    { name: 'KG Basin', values: [3, 1, 2, 6, 0, 1, 2, 0, 1] },
  ];

  const handleConfirmPsif = async (id) => {
    const report = reports.find(r => r.id === id);
    if (!report) return;
    try {
      await correctVerdict(report.verdictId, "admin_user", "P_SIF", "Confirmed by user");
      setReports((prev) =>
        prev.map((r) => (r.id === id ? { ...r, verdict: 'P-SIF', reviewStatus: 'Reviewed' } : r))
      );
    } catch (err) {
      alert("Failed to confirm: " + err.message);
    }
  };

  const handleMarkNonSif = async (id) => {
    const report = reports.find(r => r.id === id);
    if (!report) return;
    try {
      await correctVerdict(report.verdictId, "admin_user", "NON_EVENT", "Marked as non-event");
      setReports((prev) =>
        prev.map((r) => (r.id === id ? { ...r, verdict: 'Non-Event', reviewStatus: 'Reviewed' } : r))
      );
    } catch (err) {
      alert("Failed to mark non-sif: " + err.message);
    }
  };

  const handleAgreeAllNonEvents = async () => {
    // Note: A real implementation would batch update all Non-Events on the backend
    setReports((prev) =>
      prev.map((r) =>
        r.verdict === 'Non-Event' ? { ...r, reviewStatus: 'Auto-resolved' } : r
      )
    );
  };

  const getCellBg = (val) => {
    if (val === 0) return 'bg-transparent text-gray-400';
    if (val <= 2) return 'bg-[#d2e2f3] text-[#1c3a63] font-medium';
    if (val <= 4) return 'bg-[#98bce3] text-[#0f2e56] font-semibold';
    if (val <= 6) return 'bg-[#4f8cc9] text-white font-bold';
    return 'bg-[#215f9e] text-white font-bold';
  };

  const renderVerdictBadge = (verdict) => {
    switch (verdict) {
      case 'P-SIF':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#fdeded] px-2 py-0.5 text-[11px] font-bold text-[#d32f2f] border border-red-200">
            <span className="h-1.5 w-1.5 bg-[#d32f2f] rounded-xs" /> P-SIF
          </span>
        );
      case 'Exposure':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#fff8e1] px-2 py-0.5 text-[11px] font-semibold text-[#b78103] border border-amber-200">
            <span className="h-1.5 w-1.5 bg-[#b78103] rounded-xs" /> Exposure
          </span>
        );
      case 'Non-Event':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#e8f5e9] px-2 py-0.5 text-[11px] font-medium text-[#2e7d32] border border-green-200">
            ✓ Non-Event
          </span>
        );
      case '? Insufficient':
        return (
          <span className="inline-flex items-center rounded bg-[#ede7f6] px-2 py-0.5 text-[11px] font-medium text-[#5e35b1]">
            ? Insufficient
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600">
            · Unclassified
          </span>
        );
    }
  };

  return (
    <main className="flex-1 p-5 md:p-7 space-y-6 overflow-x-hidden text-[#1e293b]">
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#0f2e56] border-t-transparent"></div>
        </div>
      ) : reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-white border border-gray-200 rounded-lg shadow-sm">
          <div className="flex items-center justify-center w-16 h-16 bg-gray-50 rounded-full mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path>
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">No reports in the triage queue</h3>
          <p className="text-sm text-gray-500 max-w-sm text-center">
            Analyse some safety reports first — they'll appear here for review when the model flags them.
          </p>
        </div>
      ) : (
        <>
          <TriageAnalytics
            filters={filters}
            setFilters={setFilters}
            heatmapRules={heatmapRules}
            heatmapSites={heatmapSites}
            reports={reports}
            selectedReportId={selectedReportId}
            setSelectedReportId={setSelectedReportId}
            getCellBg={getCellBg}
          />

          <TriageQueue
            reports={reports}
            selectedReportId={selectedReportId}
            setSelectedReportId={setSelectedReportId}
            handleConfirmPsif={handleConfirmPsif}
            handleMarkNonSif={handleMarkNonSif}
            handleAgreeAllNonEvents={handleAgreeAllNonEvents}
            renderVerdictBadge={renderVerdictBadge}
          />
        </>
      )}
    </main>
  );
}