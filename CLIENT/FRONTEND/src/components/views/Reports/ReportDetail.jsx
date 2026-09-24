import React from 'react';

import ReportOverview from './ReportDetail/ReportOverview';
import ReportEvidence from './ReportDetail/ReportEvidence';

export default function ReportDetail({ data }) {
  if (!data) {
    return (
      <div className="min-h-125 flex items-center justify-center text-slate-400">
        <p className="text-sm">
          Select a report to view its details
        </p>
      </div>
    );
  }

  const report = data?.report || {};
  const verdict = data?.verdict || {};
  const spans = data?.spans || [];

  const fullOutput = verdict?.full_output || {};

  return (
    <div className="p-4 sm:p-5 lg:p-6 space-y-5 min-w-0">
      <ReportOverview
        report={report}
        verdict={verdict}
        fullOutput={fullOutput}
      />

      <ReportEvidence
        report={report}
        verdict={verdict}
        spans={spans}
        fullOutput={fullOutput}
      />
    </div>
  );
}