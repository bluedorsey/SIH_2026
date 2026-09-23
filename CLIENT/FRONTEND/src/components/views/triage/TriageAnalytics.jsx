import React from 'react';
import { ChevronDown, X, Sun, Download, AlertTriangle } from 'lucide-react';

export default function TriageAnalytics({
  filters,
  setFilters,
  heatmapRules,
  heatmapSites,
  reports,
  selectedReportId,
  setSelectedReportId,
  getCellBg
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="relative">
            <select
              value={filters.timeRange}
              onChange={(e) => setFilters({ ...filters, timeRange: e.target.value })}
              className="appearance-none rounded-lg border border-gray-300 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
            >
              <option>This week</option>
              <option>Last 30 days</option>
              <option>Quarter to date</option>
            </select>
            <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
          </div>

          <div className="relative">
            <select
              value={filters.site}
              onChange={(e) => setFilters({ ...filters, site: e.target.value })}
              className="appearance-none rounded-lg border border-gray-300 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
            >
              <option value="All">Site: All</option>
              <option value="Duliajan">Site 7 (Duliajan)</option>
              <option value="Moran">Moran</option>
              <option value="Baghjan">Baghjan</option>
            </select>
            <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
          </div>

          <div className="relative">
            <select
              value={filters.activity}
              onChange={(e) => setFilters({ ...filters, activity: e.target.value })}
              className="appearance-none rounded-lg border border-gray-300 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
            >
              <option>Activity: All</option>
              <option>Workover rig</option>
              <option>Drilling</option>
              <option>Hot work</option>
            </select>
            <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
          </div>

          <div className="relative">
            <select
              value={filters.rule}
              onChange={(e) => setFilters({ ...filters, rule: e.target.value })}
              className="appearance-none rounded-lg border border-gray-300 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
            >
              <option>Rule: All</option>
              <option>LF (Line of Fire)</option>
              <option>EI (Energy Isolation)</option>
              <option>WH (Work at Height)</option>
            </select>
            <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
          </div>

          <div className="relative">
            <select
              value={filters.verdict}
              onChange={(e) => setFilters({ ...filters, verdict: e.target.value })}
              className="appearance-none rounded-lg border border-gray-300 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
            >
              <option>Verdict: All</option>
              <option>P-SIF</option>
              <option>Exposure</option>
              <option>Non-Event</option>
            </select>
            <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
          </div>

          <div className="relative">
            <select
              value={filters.review}
              onChange={(e) => setFilters({ ...filters, review: e.target.value })}
              className="appearance-none rounded-lg border border-gray-300 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
            >
              <option>Review: Unreviewed</option>
              <option>Review: All</option>
              <option>Review: Reviewed</option>
            </select>
            <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 rounded-full bg-[#fef3c7] px-3 py-1 font-semibold text-[#92400e]">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span>Offline · 06:40 · 3 pending</span>
          </div>

          <div className="flex items-center gap-2 border-l border-gray-200 pl-3 text-gray-600">
            <button className="flex items-center gap-1 hover:text-black">
              <Sun size={13} /> Light
            </button>
            <button className="flex items-center gap-1 hover:text-black">
              Field
            </button>
            <button
              onClick={() => alert('Exporting CSV...')}
              className="flex items-center gap-1 hover:text-black cursor-pointer"
            >
              <Download size={13} /> Export
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="font-medium text-gray-700">State: Live</span>
          </div>

          <div className="flex items-center gap-2 border-l border-gray-200 pl-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#1e40af] text-[10px] font-bold text-white">
              SB
            </div>
            <span className="font-semibold text-gray-800">S. Borgohain</span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 pt-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-gray-400 uppercase tracking-wider text-[10px]">
            Filters
          </span>
          <span className="flex items-center gap-1 rounded-md bg-sky-50 px-2.5 py-1 text-sky-800 font-medium border border-sky-200">
            This week
            <X size={12} className="cursor-pointer" />
          </span>
          <span className="flex items-center gap-1 rounded-md bg-sky-50 px-2.5 py-1 text-sky-800 font-medium border border-sky-200">
            Review: unreviewed
            <X size={12} className="cursor-pointer" />
          </span>
          <button
            onClick={() =>
              setFilters({
                timeRange: 'This week',
                site: 'All',
                activity: 'All',
                rule: 'All',
                verdict: 'All',
                review: 'All'
              })
            }
            className="text-xs text-blue-600 hover:underline ml-1 font-medium cursor-pointer"
          >
            clear all
          </button>
        </div>
        <div className="text-[11px] text-gray-400">
          All sites → Duliajan → Workover rig → Line of Fire
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs font-bold text-gray-600 uppercase tracking-wider">
            <span className="h-2 w-2 rounded-full bg-[#dc2626]" />
            <span>P-SIF this week</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0e1d2c]">9</span>
            <span className="text-xs font-semibold text-[#dc2626]">▲ 12%</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">fatal potential · nothing happened</p>
          <p className="mt-0.5 text-[10px] text-gray-400">· 6 unreviewed</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-1.5 text-xs font-bold text-gray-600 uppercase tracking-wider">
            <span className="h-2 w-2 rounded-xs border border-gray-400" />
            <span>Exposure + Capacity</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0e1d2c]">41</span>
            <span className="text-xs font-semibold text-[#059669]">▼ 4%</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">control missing or marginal · 18 unreviewed</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-bold text-gray-600 uppercase tracking-wider">
            Reports Ingested
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0e1d2c]">186</span>
            <span className="text-xs font-semibold text-[#dc2626]">▲ 12</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">last batch 14:32 today · 47 reports</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-bold text-gray-600 uppercase tracking-wider">
            Uncertain Lane
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0e1d2c]">24</span>
            <span className="text-xs font-semibold text-[#dc2626]">▲ 6</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">reader ran on all · 12.9% of intake</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-bold text-gray-600 uppercase tracking-wider">
            Awaiting Review
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0e1d2c]">23</span>
            <span className="text-xs font-semibold text-[#dc2626]">▲ 8</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">oldest 3 days · est. 45 min</p>
        </div>
      </div>
 
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Heatmap */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-xs lg:col-span-5">
          <div className="text-xs font-bold text-gray-900 border-b border-gray-100 pb-2">
            A · Site × Rule{' '}
            <span className="font-normal text-gray-400">
              P-SIF + Exposure · click a cell to filter
            </span>
          </div>

          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-center text-xs">
              <thead>
                <tr className="text-[11px] text-gray-400">
                  <th className="text-left font-normal pb-2">Site</th>
                  {heatmapRules.map((r) => (
                    <th key={r} className="font-semibold px-1 pb-2">
                      {r}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {heatmapSites.map((row) => (
                  <tr key={row.name} className="hover:bg-gray-50">
                    <td className="text-left font-medium py-1.5 pr-2 text-gray-700 truncate max-w-30">
                      {row.name}
                    </td>
                    {row.values.map((v, i) => (
                      <td key={i} className="p-0.5">
                        <button
                          onClick={() => {
                            setFilters({ ...filters, site: row.name, rule: heatmapRules[i] });
                          }}
                          className={`h-6 w-6 rounded text-[11px] leading-6 cursor-pointer transition hover:opacity-80 ${getCellBg(
                            v
                          )}`}
                        >
                          {v === 0 ? '-' : v}
                        </button>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center justify-between text-[10px] text-gray-400 pt-2 border-t border-gray-100">
            <div className="flex items-center gap-1">
              <span>fewer</span>
              <span className="h-2 w-2 rounded-xs bg-[#d2e2f3]" />
              <span className="h-2 w-2 rounded-xs bg-[#98bce3]" />
              <span className="h-2 w-2 rounded-xs bg-[#4f8cc9]" />
              <span className="h-2 w-2 rounded-xs bg-[#215f9e]" />
              <span>more</span>
            </div>
            <span>hover a column for rule name</span>
          </div>
        </div>
 
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-xs lg:col-span-4 flex flex-col justify-between">
          <div>
            <div className="text-xs font-bold text-gray-900">
              B · Verdict mix vs last period
            </div>
            <div className="mt-4 space-y-3 text-xs">
              <div>
                <div className="flex justify-between text-gray-500 mb-1 text-[11px]">
                  <span>This period</span>
                  <span>186 reports</span>
                </div>
                <div className="h-3 w-full flex rounded-full overflow-hidden">
                  <div style={{ width: '12%' }} className="bg-[#dc2626]" />
                  <div style={{ width: '22%' }} className="bg-[#f59e0b]" />
                  <div style={{ width: '15%' }} className="bg-[#fcd34d]" />
                  <div style={{ width: '51%' }} className="bg-[#15803d]" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-gray-500 mb-1 text-[11px]">
                  <span>Last period</span>
                  <span>174 reports</span>
                </div>
                <div className="h-3 w-full flex rounded-full overflow-hidden">
                  <div style={{ width: '8%' }} className="bg-[#dc2626]" />
                  <div style={{ width: '20%' }} className="bg-[#f59e0b]" />
                  <div style={{ width: '10%' }} className="bg-[#fcd34d]" />
                  <div style={{ width: '62%' }} className="bg-[#15803d]" />
                </div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2.5 text-[11px] text-gray-500">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#dc2626]" /> P-SIF
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#f59e0b]" /> Exposure
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#fcd34d]" /> Uncertain
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#15803d]" /> Non-Event
              </span>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="text-xs font-semibold text-gray-800">
              P-SIF share 4.2% → <span className="text-[#dc2626]">5.1% ▲</span>
            </div>
            <p className="text-[11px] italic text-gray-400 mt-0.5">
              The pile is getting worse, not the reporting.
            </p>
          </div>
        </div>
 
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-xs lg:col-span-3 flex flex-col justify-between">
          <div>
            <div className="text-xs font-bold text-gray-900">
              C · Volume funnel · this period
            </div>
            <div className="mt-4 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Ingested</span>
                <span className="font-mono font-medium text-gray-800">3,200</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Fast path</span>
                <span className="font-mono font-medium text-gray-800">2,800</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Uncertain lane</span>
                <span className="font-mono font-medium text-gray-800">400</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">P-SIF flagged</span>
                <span className="font-mono text-red-600 font-bold">85</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Human reviewed</span>
                <span className="font-mono font-medium text-gray-800">23</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex items-center justify-between text-center">
              <div>
                <span className="text-base font-bold text-gray-800">87%</span>
                <p className="text-[10px] text-gray-400">auto-resolved</p>
              </div>
              <div>
                <span className="text-base font-bold text-gray-800">6.6%</span>
                <p className="text-[10px] text-gray-400">human-reviewed</p>
              </div>
              <div>
                <span className="text-base font-bold text-gray-800">26%</span>
                <p className="text-[10px] text-gray-400">override rate</p>
              </div>
            </div>
          </div>
        </div>
      </div>
 
      <div className="rounded-xl border border-red-200 bg-[#fff8f8] p-4">
        <div className="flex items-center gap-2 text-xs font-bold text-red-700">
          <AlertTriangle size={15} />
          <span>Unreviewed P-SIF — act first</span>
          <span className="font-normal text-red-500">· oldest 3 days · est. 45 min to clear</span>
        </div>

        <div className="mt-3 space-y-2">
          {reports
            .filter((r) => r.verdict === 'P-SIF' && r.reviewStatus === 'Unreviewed')
            .map((item) => (
              <div
                key={item.id}
                onClick={() => setSelectedReportId(item.id)}
                className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-3 shadow-xs cursor-pointer transition hover:border-red-300 ${
                  selectedReportId === item.id
                    ? 'ring-2 ring-red-400 border-transparent'
                    : 'border-gray-100'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="rounded bg-[#dc2626] px-1.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                    ■ P-SIF
                  </span>
                  <span className="text-xs font-bold text-gray-900 font-mono">{item.id}</span>
                  <p className="text-xs text-gray-700 line-clamp-1 max-w-xl">{item.text}</p>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="text-gray-500 font-medium">{item.site}</span>
                  <span className="font-bold text-red-600">{item.inQueue}</span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}