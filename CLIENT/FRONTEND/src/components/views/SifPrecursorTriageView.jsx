import React, { useState } from 'react';
import TriageAnalytics from './triage/TriageAnalytics';
import TriageQueue from './triage/TriageQueue';

export default function SifPrecursorTriageView() {
  const [filters, setFilters] = useState({
    timeRange: 'This week',
    site: 'All',
    activity: 'All',
    rule: 'All',
    verdict: 'All',
    review: 'Unreviewed'
  });

  const [selectedReportId, setSelectedReportId] = useState('OIL-2026-0914');

  const [reports, setReports] = useState([
    {
      id: 'OIL-2026-0914',
      verdict: 'P-SIF',
      site: 'Duliajan',
      date: '09 Sep',
      energy: '1,570 J',
      rule: 'LF',
      barrier: 'absent',
      role: 'Assistant Driller',
      activity: 'Workover rig',
      language: 'Hinglish · 0.94',
      fullDate: '09 Sep 2026 · 02:40',
      sourceType: 'Near-miss',
      text: 'Rig floor par tong ka 8 kg counterweight monkey board se gir gaya — worker standing 1.5 m from impact point.',
      reviewStatus: 'Unreviewed',
      inQueue: '4 h 12 m',
      energyValue: 1570
    },
    {
      id: 'OIL-2026-0911',
      verdict: 'Exposure',
      site: 'Moran',
      date: '09 Sep',
      energy: '2,400 J',
      rule: 'HW PW',
      barrier: 'absent',
      role: 'Welder',
      activity: 'Hot Work',
      language: 'English · 0.98',
      fullDate: '09 Sep 2026 · 05:15',
      sourceType: 'Observation',
      text: 'Hot work cutting near hydrocarbon gas manifold without continuous multi-gas monitor.',
      reviewStatus: 'Unreviewed',
      inQueue: '6 h 40 m',
      energyValue: 2400
    },
    {
      id: 'OIL-2026-0908',
      verdict: 'P-SIF',
      site: 'Baghjan',
      date: '09 Sep',
      energy: '-',
      rule: 'EI',
      barrier: 'unknown',
      role: 'Mechanic',
      activity: 'Pipeline Maintenance',
      language: 'Assamese / Hinglish · 0.91',
      fullDate: '09 Sep 2026 · 08:30',
      sourceType: 'Near-miss',
      text: 'Gas line-ot pressure thakiley bhi LOTO tag nai asil, valve khulise — energy not isolated before valve maintenance.',
      reviewStatus: 'Unreviewed',
      inQueue: '6 h 00 m',
      energyValue: 0
    },
    {
      id: 'OIL-2026-0905',
      verdict: '? Insufficient',
      site: 'Jorhat',
      date: '08 Sep',
      energy: 'unknown',
      rule: '-',
      barrier: 'unknown',
      role: 'Operator',
      activity: 'Routine Rounds',
      language: 'Hindi · 0.88',
      fullDate: '08 Sep 2026 · 14:10',
      sourceType: 'Observation',
      text: 'Plant area me thoda smell aa raha tha par instrument verify nahi hua.',
      reviewStatus: 'Unreviewed',
      inQueue: '1 day',
      energyValue: 0
    },
    {
      id: 'OIL-2026-0902',
      verdict: 'P-SIF',
      site: 'Naharkatiya',
      date: '08 Sep',
      energy: '8,400 J',
      rule: 'LF WH',
      barrier: 'ineffective',
      role: 'Derrickman',
      activity: 'Mast Operations',
      language: 'English · 0.96',
      fullDate: '08 Sep 2026 · 17:45',
      sourceType: 'Incident',
      text: 'Elevator link parted at 6 m and fell to the rig floor; derrickman had just stepped away from the impact zone.',
      reviewStatus: 'Unreviewed',
      inQueue: '3 days',
      energyValue: 8400
    },
    {
      id: 'OIL-2026-0899',
      verdict: 'Non-Event',
      site: 'Duliajan',
      date: '08 Sep',
      energy: 'low',
      rule: 'PPE',
      barrier: 'present',
      role: 'Store Keeper',
      activity: 'Materials Handling',
      language: 'English · 0.99',
      fullDate: '08 Sep 2026 · 11:20',
      sourceType: 'Inspection',
      text: 'Safety boots laces were untied; worker corrected immediately after prompt.',
      reviewStatus: 'Auto-resolved',
      inQueue: '-',
      energyValue: 10
    },
    {
      id: 'OIL-2026-0895',
      verdict: 'Exposure',
      site: 'KG Basin',
      date: '07 Sep',
      energy: '3,100 J',
      rule: 'CS',
      barrier: 'marginal',
      role: 'Safety Officer',
      activity: 'Vessel Entry',
      language: 'English · 0.95',
      fullDate: '07 Sep 2026 · 19:10',
      sourceType: 'Near-miss',
      text: 'Contractor entered separator vessel without standalone standby rescuer stationed at manway.',
      reviewStatus: 'Unreviewed',
      inQueue: '2 days',
      energyValue: 3100
    },
    {
      id: 'OIL-2026-0891',
      verdict: 'Unclassified',
      site: 'Rajasthan (Jodhpur)',
      date: '07 Sep',
      energy: '-',
      rule: 'DR',
      barrier: 'unknown',
      role: 'Driver',
      activity: 'Logistics Transport',
      language: 'Hinglish · 0.89',
      fullDate: '07 Sep 2026 · 22:00',
      sourceType: 'Observation',
      text: 'Heavy vehicle convoy speed governor bypassed on desert stretch.',
      reviewStatus: 'Unreviewed',
      inQueue: '2 days',
      energyValue: 0
    }
  ]);

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

  const handleConfirmPsif = (id) => {
    setReports((prev) =>
      prev.map((r) => (r.id === id ? { ...r, verdict: 'P-SIF', reviewStatus: 'Reviewed' } : r))
    );
  };

  const handleMarkNonSif = (id) => {
    setReports((prev) =>
      prev.map((r) => (r.id === id ? { ...r, verdict: 'Non-Event', reviewStatus: 'Reviewed' } : r))
    );
  };

  const handleAgreeAllNonEvents = () => {
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
    </main>
  );
}