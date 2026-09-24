import React from 'react';
import {
  BarChart2,
  Search,
  FileText,
  Loader2,
} from 'lucide-react';

export default function ReportRegistry({
  reports,
  loading,
  searchTerm,
  setSearchTerm,
  selectedReportId,
  setSelectedReportId,
}) {

  // ============================================================
  // VERDICT BADGE
  // ============================================================
  const getVerdictBadge = (verdict) => {
    const value = String(verdict || '').toUpperCase();

    if (value === 'NON_EVENT') {
      return 'bg-emerald-600 text-white';
    }

    if (
      value === 'INSUFFICIENT' ||
      value === 'OUT_OF_SCOPE'
    ) {
      return 'bg-slate-500 text-white';
    }

    if (
      value === 'H_SIF' ||
      value === 'P_SIF'
    ) {
      return 'bg-red-600 text-white';
    }

    if (value === 'LOW_ENERGY') {
      return 'bg-teal-700 text-white';
    }

    if (
      value === 'EXPOSURE' ||
      value === 'CAPACITY'
    ) {
      return 'bg-orange-500 text-white';
    }

    if (value === 'SUCCESS') {
      return 'bg-emerald-600 text-white';
    }

    return 'bg-slate-500 text-white';
  };

  // ============================================================
  // ROW BACKGROUND
  // ============================================================
  const getRowClass = (verdict) => {
    const value = String(verdict || '').toUpperCase();

    if (value === 'NON_EVENT') {
      return 'bg-emerald-50 hover:bg-emerald-100';
    }

    if (
      value === 'H_SIF' ||
      value === 'P_SIF'
    ) {
      return 'bg-red-50 hover:bg-red-100';
    }

    if (
      value === 'EXPOSURE' ||
      value === 'CAPACITY'
    ) {
      return 'bg-orange-50 hover:bg-orange-100';
    }

    if (value === 'LOW_ENERGY') {
      return 'bg-teal-50 hover:bg-teal-100';
    }

    if (
      value === 'INSUFFICIENT' ||
      value === 'OUT_OF_SCOPE'
    ) {
      return 'bg-slate-50 hover:bg-slate-100';
    }

    return 'hover:bg-slate-50';
  };

  // ============================================================
  // EXPORT CSV
  // ============================================================
  const exportCSV = () => {

    const headers = [
      'Incident ID',
      'Incident',
      'Verdict',
      'Date',
      'Site',
      'Location',
      'LSR',
    ];

    const rows = reports.map((report) => {

      const incident =
        report.raw_text ||
        `Incident Report - ${report.site_code || 'Unknown'}`;

      const location =
        report.metadata?.location || 'N/A';

      return [
        report.report_id,
        incident,
        report.verdict || 'Unknown',
        new Date(
          report.ingested_at
        ).toLocaleDateString(),
        report.site_code || 'Unknown',
        location,
        report.lsr_primary || 'N/A',
      ];
    });

    const csv = [
      headers.join(','),
      ...rows.map((row) =>
        row
          .map((cell) =>
            `"${String(cell).replace(/"/g, '""')}"`
          )
          .join(',')
      ),
    ].join('\n');

    const blob = new Blob(
      [csv],
      { type: 'text/csv;charset=utf-8;' }
    );

    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');

    link.href = url;
    link.download = 'reports_export.csv';

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[650px] lg:h-[800px] min-w-0">

      {/* ======================================================
          HEADER
      ====================================================== */}
      <div className="p-4 border-b border-slate-100">

        <div className="flex items-center gap-2 mb-3">

          <BarChart2
            size={16}
            className="text-teal-700"
          />

          <h2 className="text-sm font-bold text-slate-800">
            Report Registry
          </h2>

        </div>

        {/* Search + Export */}
        <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">

          {/* Search */}
          <div className="relative w-full sm:max-w-sm">

            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              type="text"
              value={searchTerm}
              onChange={(e) =>
                setSearchTerm(e.target.value)
              }
              placeholder="Search reports..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-600 focus:border-teal-600"
            />

          </div>

          {/* Export */}
          <button
            onClick={exportCSV}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-teal-200 bg-teal-50 text-teal-700 text-xs font-semibold hover:bg-teal-100 transition-colors shrink-0"
          >

            <FileText size={14} />

            Export CSV

          </button>

        </div>

      </div>


      {/* ======================================================
          TABLE
      ====================================================== */}
      <div className="flex-1 overflow-auto">

        {loading ? (

          <div className="h-full min-h-[300px] flex flex-col items-center justify-center gap-3 text-slate-500">

            <Loader2
              size={26}
              className="animate-spin text-teal-600"
            />

            <p className="text-xs font-medium">
              Loading reports...
            </p>

          </div>

        ) : reports.length === 0 ? (

          <div className="h-full min-h-[300px] flex flex-col items-center justify-center gap-2 text-slate-400">

            <FileText size={30} />

            <p className="text-xs font-medium">
              No reports found
            </p>

          </div>

        ) : (

          <table className="w-full min-w-[900px] text-left text-xs">

            {/* TABLE HEADER */}
            <thead className="sticky top-0 z-20 bg-slate-50 border-b border-slate-200">

              <tr className="text-slate-500 font-bold">

                <th className="px-3 py-3">
                  Incident ID
                </th>

                <th className="px-3 py-3">
                  Incident
                </th>

                <th className="px-3 py-3">
                  Verdict
                </th>

                <th className="px-3 py-3">
                  Date
                </th>

                <th className="px-3 py-3">
                  Site
                </th>

                <th className="px-3 py-3">
                  Location
                </th>

                <th className="px-3 py-3">
                  LSR
                </th>

              </tr>

            </thead>


            {/* TABLE BODY */}
            <tbody className="divide-y divide-slate-100">

              {reports.map((report) => {

                const selected =
                  selectedReportId ===
                  report.report_id;

                return (

                  <tr
                    key={report.report_id}
                    onClick={() =>
                      setSelectedReportId(
                        report.report_id
                      )
                    }
                    className={`
                      cursor-pointer
                      transition-colors
                      border-l-4
                      ${
                        selected
                          ? 'border-l-teal-600'
                          : 'border-l-transparent'
                      }
                      ${getRowClass(
                        report.verdict
                      )}
                    `}
                  >

                    {/* ID */}
                    <td
                      className="px-3 py-3 font-mono text-[10px] text-slate-600 max-w-[110px] truncate"
                      title={report.report_id}
                    >
                      {report.report_id}
                    </td>


                    {/* INCIDENT */}
                    <td className="px-3 py-3 font-semibold text-slate-800">

                      Incident Report -{' '}

                      {report.site_code ||
                        'Unknown'}

                    </td>


                    {/* VERDICT */}
                    <td className="px-3 py-3">

                      <span
                        className={`
                          inline-flex
                          px-2
                          py-1
                          rounded-md
                          text-[10px]
                          font-bold
                          ${getVerdictBadge(
                            report.verdict
                          )}
                        `}
                      >

                        {report.verdict ||
                          'UNKNOWN'}

                      </span>

                    </td>


                    {/* DATE */}
                    <td className="px-3 py-3 text-slate-600 font-mono">

                      {report.ingested_at
                        ? new Date(
                            report.ingested_at
                          ).toLocaleDateString()
                        : 'N/A'}

                    </td>


                    {/* SITE */}
                    <td className="px-3 py-3 text-slate-700">

                      {report.site_code ||
                        'Unknown'}

                    </td>


                    {/* LOCATION */}
                    <td className="px-3 py-3 text-slate-500">

                      {report.metadata?.location ||
                        'N/A'}

                    </td>


                    {/* LSR */}
                    <td
                      className="px-3 py-3 text-slate-700 font-medium max-w-[140px] truncate"
                      title={report.lsr_primary}
                    >

                      {report.lsr_primary ||
                        'No LSR'}

                    </td>

                  </tr>

                );

              })}

            </tbody>

          </table>

        )}

      </div>

    </div>
  );
}