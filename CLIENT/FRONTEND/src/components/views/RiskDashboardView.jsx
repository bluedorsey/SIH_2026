import React, { useState, useEffect } from 'react';
import { ChevronDown, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { getPatterns, getSites, getQueueCounts, getReports } from '../../services/api';

export default function RiskDashboardView() {
  // Filters state
  const [dateRange, setDateRange] = useState('Last 30 days');
  const [site, setSite] = useState('All Sites');
  const [activity, setActivity] = useState('All Activities');
  const [lsr, setLsr] = useState('All Rules');
  const [reportType, setReportType] = useState('All Types');
  const [riskLevel, setRiskLevel] = useState('All Levels');

  // Chart view toggle
  const [activityMode, setActivityMode] = useState('Volume'); 
  const [hoveredMonthIndex, setHoveredMonthIndex] = useState(0); 

  // Data State
  const [queueCounts, setQueueCounts] = useState({ high: 0, medium: 0, low: 0, insufficient: 0 });
  const [monthlyData, setMonthlyData] = useState([{ month: 'N/A', sif: 0, total: 0 }, { month: 'N/A ', sif: 0, total: 0 }]);
  const [activityData, setActivityData] = useState([]);
  const [siteRankings, setSiteRankings] = useState([]);

  useEffect(() => {
    async function loadDashboard() {
      try {
        // Fetch sites and all reports
        const [sitesRes, reportsRes] = await Promise.all([
          getSites(1, 20),
          getReports(1, 1000)
        ]);
        
        const allReports = reportsRes?.data || [];
        
        let high = 0, medium = 0, low = 0, insufficient = 0;
        const monthMap = {};
        const activityMap = {};

        allReports.forEach(r => {
          const v = String(r.verdict || "").toUpperCase();
          let isSif = false;
          
          if (v === "H_SIF" || v === "P_SIF" || v.includes("HIGH")) {
            high++;
            isSif = true;
          } else if (v === "CAPACITY" || v === "EXPOSURE" || v.includes("MEDIUM")) {
            medium++;
            isSif = true;
          } else if (v === "LOW_ENERGY" || v === "SUCCESS" || v === "NON_EVENT" || v.includes("LOW")) {
            low++;
          } else {
            insufficient++;
          }
          
          const d = new Date(r.ingested_at);
          if (!isNaN(d.getTime())) {
            const m = d.toLocaleString('default', { month: 'short' }); // e.g. "Sep"
            const yearStr = d.getFullYear().toString().slice(2);
            const key = `${m} '${yearStr}`;
            if (!monthMap[key]) monthMap[key] = { month: key, total: 0, sif: 0, time: d.getTime() };
            monthMap[key].total++;
            if (isSif) monthMap[key].sif++;
          }
          
          const rule = r.lsr_primary || 'Other';
          if (!activityMap[rule]) activityMap[rule] = 0;
          activityMap[rule]++;
        });
        
        setQueueCounts({ high, medium, low, insufficient });
        
        const sortedMonths = Object.values(monthMap).sort((a,b) => a.time - b.time);
        if (sortedMonths.length === 0) {
           sortedMonths.push({ month: 'N/A', total: 0, sif: 0 });
           sortedMonths.push({ month: 'N/A ', total: 0, sif: 0 });
        } else if (sortedMonths.length === 1) {
           sortedMonths.unshift({ month: 'Prev', total: 0, sif: 0 });
        }
        setMonthlyData(sortedMonths);
        
        const colors = ['bg-[#dc2626]', 'bg-[#ea580c]', 'bg-[#d97706]', 'bg-[#ca8a04]', 'bg-[#0f766e]', 'bg-[#0d9488]', 'bg-slate-500'];
        const totalActivityCount = Object.values(activityMap).reduce((a,b)=>a+b, 0) || 1;
        const sortedActivities = Object.entries(activityMap)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 6)
          .map(([label, count], i) => ({
            label: label.replace(/_/g, ' '),
            count,
            density: ((count / totalActivityCount) * 100).toFixed(1) + '%',
            color: colors[i % colors.length]
          }));
        setActivityData(sortedActivities);

        const sitesData = sitesRes?.data || [];
        const mappedSites = sitesData.map((s, idx) => ({
          rank: `0${idx + 1}`,
          name: s.site_name || s.name || 'Unknown',
          reports: s.total_reports || 0,
          sif: s.sif_count || 0,
          density: `${(s.sif_density_pct || 0).toFixed(1)}%`,
          densityVal: s.sif_density_pct || 0,
          trend: 'neutral',
          risk: s.high_risk_flag ? 'HIGH' : 'ROUTINE'
        }));
        
        setSiteRankings(mappedSites);
      } catch(err) {
        console.error("Dashboard fetch error:", err);
      }
    }
    loadDashboard();
  }, []);

  // SVG Chart Calculations
  const chartW = 600;
  const chartH = 200;
  const padX = 30;
  const padY = 20;

  const getX = (idx) => padX + (idx / (monthlyData.length - 1)) * (chartW - 2 * padX);
  const getY = (val) => chartH - padY - (val / 80) * (chartH - 2 * padY);

  // Generate smooth cubic bezier SVG curves
  const makePath = (key) => {
    return monthlyData.reduce((acc, pt, i) => {
      const x = getX(i);
      const y = getY(pt[key]);
      if (i === 0) return `M ${x} ${y}`;
      const prevX = getX(i - 1);
      const prevY = getY(monthlyData[i - 1][key]);
      const cx1 = prevX + (x - prevX) / 2;
      const cx2 = cx1;
      return `${acc} C ${cx1} ${prevY}, ${cx2} ${y}, ${x} ${y}`;
    }, '');
  };

  const sifPath = makePath('sif');
  const totalPath = makePath('total');

  return (
    <main className="flex-1 p-6 md:p-8 space-y-6 text-[#1c2a38] overflow-x-hidden">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-2xl font-bold text-[#0e1d2c]">Risk Intelligence</h1>
        <p className="mt-1 text-xs sm:text-sm text-gray-500">
          Where are SIF precursors concentrating?
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2.5 text-xs">
        {/* Date Range */}
        <div className="relative">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="appearance-none rounded-lg border border-gray-200 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
          >
            <option>Date Range: Last 30 days</option>
            <option>Date Range: Last 90 days</option>
            <option>Date Range: Year to date</option>
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
        </div>

        {/* Site */}
        <div className="relative">
          <select
            value={site}
            onChange={(e) => setSite(e.target.value)}
            className="appearance-none rounded-lg border border-gray-200 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
          >
            <option>Site: All Sites</option>
            <option>Duliajan</option>
            <option>Digboi</option>
            <option>Bokakhat</option>
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
        </div>

        {/* Activity */}
        <div className="relative">
          <select
            value={activity}
            onChange={(e) => setActivity(e.target.value)}
            className="appearance-none rounded-lg border border-gray-200 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
          >
            <option>Activity: All Activities</option>
            <option>Lifting Operations</option>
            <option>Energy Isolation</option>
            <option>Confined Space</option>
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
        </div>

        {/* LSR */}
        <div className="relative">
          <select
            value={lsr}
            onChange={(e) => setLsr(e.target.value)}
            className="appearance-none rounded-lg border border-gray-200 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
          >
            <option>LSR: All Rules</option>
            <option>Line of Fire</option>
            <option>Safe Mechanical Lifting</option>
            <option>Work at Height</option>
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
        </div>

        {/* Report Type */}
        <div className="relative">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="appearance-none rounded-lg border border-gray-200 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
          >
            <option>Report Type: All Types</option>
            <option>Near-miss</option>
            <option>Observation</option>
            <option>Incident</option>
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
        </div>

        {/* Risk Level */}
        <div className="relative">
          <select
            value={riskLevel}
            onChange={(e) => setRiskLevel(e.target.value)}
            className="appearance-none rounded-lg border border-gray-200 bg-white px-3 py-1.5 pr-7 font-medium text-gray-700 shadow-xs focus:outline-hidden"
          >
            <option>Risk: All Levels</option>
            <option>High</option>
            <option>Medium</option>
            <option>Routine</option>
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-2 top-2.5 text-gray-400" />
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-xs">
          <div className="text-3xl font-extrabold text-[#dc2626]">{queueCounts.high || 0}</div>
          <div className="mt-2 text-xs font-semibold text-gray-800">
            High Risk Reports
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-xs">
          <div className="text-3xl font-extrabold text-[#d97706]">{queueCounts.medium || 0}</div>
          <div className="mt-2 text-xs font-semibold text-gray-800">
            Medium Risk Reports
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-xs">
          <div className="text-3xl font-extrabold text-[#0e7490]">{queueCounts.low || 0}</div>
          <div className="mt-2 text-xs font-semibold text-gray-800">
            Low Risk Reports
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-xs">
          <div className="text-3xl font-extrabold text-[#2563eb]">{queueCounts.insufficient || 0}</div>
          <div className="mt-2 text-xs font-semibold text-gray-800">
            Insufficient Data
          </div>
        </div>
      </div>

      {/* Middle Section: Trends & Activity Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Monthly Trend Spline Line Chart */}
        <div className="lg:col-span-8 rounded-xl border border-gray-100 bg-white p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-gray-900">
              SIF-potential reports over time
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Monthly — total observations vs SIF-potential
            </p>
          </div>

          <div className="relative mt-6 w-full overflow-hidden select-none">
            <svg
              viewBox={`0 0 ${chartW} ${chartH + 20}`}
              className="w-full h-56 overflow-visible"
            >
              {/* Grid Lines */}
              {[0, 20, 40, 60, 80].map((val) => {
                const y = getY(val);
                return (
                  <g key={val}>
                    <line
                      x1={padX}
                      y1={y}
                      x2={chartW - padX}
                      y2={y}
                      stroke="#f1f5f9"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={padX - 8}
                      y={y + 3}
                      textAnchor="end"
                      className="text-[10px] fill-gray-400 font-mono"
                    >
                      {val}
                    </text>
                  </g>
                );
              })}

              {/* Total Observations Smooth Spline */}
              <path
                d={totalPath}
                fill="none"
                stroke="#cbd5e1"
                strokeWidth="2.2"
                className="transition-all duration-700 ease-out"
              />

              {/* SIF-Potential Smooth Spline */}
              <path
                d={sifPath}
                fill="none"
                stroke="#dc2626"
                strokeWidth="2.5"
                className="transition-all duration-700 ease-out"
              />

              {/* Month X-Axis labels */}
              {monthlyData.map((d, i) => (
                <text
                  key={d.month}
                  x={getX(i)}
                  y={chartH + 10}
                  textAnchor="middle"
                  className="text-[10px] fill-gray-500 font-medium"
                >
                  {d.month}
                </text>
              ))}

              {/* Hover Trigger Vertical Line and Active Circles */}
              {hoveredMonthIndex !== null && monthlyData[hoveredMonthIndex] && (
                <g>
                  {/* Vertical Tracking Line */}
                  <line
                    x1={getX(hoveredMonthIndex)}
                    y1={padY}
                    x2={getX(hoveredMonthIndex)}
                    y2={chartH - padY}
                    stroke="#e2e8f0"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                  />

                  {/* Red SIF point indicator */}
                  <circle
                    cx={getX(hoveredMonthIndex)}
                    cy={getY(monthlyData[hoveredMonthIndex].sif)}
                    r="5"
                    fill="#dc2626"
                    stroke="#fff"
                    strokeWidth="2"
                    className="transition-all duration-200"
                  />

                  {/* Gray Total point indicator */}
                  <circle
                    cx={getX(hoveredMonthIndex)}
                    cy={getY(monthlyData[hoveredMonthIndex].total)}
                    r="4.5"
                    fill="#94a3b8"
                    stroke="#fff"
                    strokeWidth="2"
                    className="transition-all duration-200"
                  />
                </g>
              )}

              {/* Invisible Full Height Hit-Testing Bars for Smooth Hover Interaction */}
              {monthlyData.map((_, i) => {
                const x = getX(i);
                const barWidth = (chartW - 2 * padX) / monthlyData.length;
                return (
                  <rect
                    key={i}
                    x={x - barWidth / 2}
                    y={0}
                    width={barWidth}
                    height={chartH}
                    fill="transparent"
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredMonthIndex(i)}
                  />
                );
              })}
            </svg>

            {/* Custom Interactive Tooltip Pill matching screenshot */}
            {hoveredMonthIndex !== null && monthlyData[hoveredMonthIndex] && (
              <div
                className="absolute z-10 pointer-events-none rounded-xl border border-gray-100 bg-white/95 backdrop-blur-xs p-3 shadow-lg transition-all duration-200 -translate-x-1/2"
                style={{
                  left: `${(getX(hoveredMonthIndex) / chartW) * 100}%`,
                  top: '15%'
                }}
              >
                <div className="text-xs font-bold text-gray-800">
                  {monthlyData[hoveredMonthIndex].month}
                </div>
                <div className="mt-1 text-xs font-semibold text-[#dc2626]">
                  SIF-potential : {monthlyData[hoveredMonthIndex].sif}
                </div>
                <div className="mt-0.5 text-xs text-gray-400">
                  Total : {monthlyData[hoveredMonthIndex].total}
                </div>
              </div>
            )}
          </div>
 
          <div className="mt-4 flex items-center justify-center gap-4 text-xs font-medium text-gray-500">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#dc2626]" />
              <span className="text-[#dc2626]">SIF-potential</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#94a3b8]" />
              <span>Total</span>
            </div>
          </div>
        </div>
 
        <div className="lg:col-span-4 rounded-xl border border-gray-100 bg-white p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Activity breakdown</h2>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  Activities generating most SIF precursors
                </p>
              </div>

              {/* Volume / Density Switcher */}
              <div className="flex rounded-lg bg-gray-100 p-0.5 text-xs font-medium">
                <button
                  onClick={() => setActivityMode('Volume')}
                  className={`rounded-md px-2.5 py-1 transition cursor-pointer ${
                    activityMode === 'Volume'
                      ? 'bg-[#004e47] text-white shadow-xs font-semibold'
                      : 'text-gray-600 hover:text-black'
                  }`}
                >
                  Volume
                </button>
                <button
                  onClick={() => setActivityMode('Density')}
                  className={`rounded-md px-2.5 py-1 transition cursor-pointer ${
                    activityMode === 'Density'
                      ? 'bg-[#004e47] text-white shadow-xs font-semibold'
                      : 'text-gray-600 hover:text-black'
                  }`}
                >
                  Density
                </button>
              </div>
            </div>

            {/* Horizontal Bar Chart List */}
            <div className="mt-6 space-y-3.5">
              {activityData.map((act) => {
                const maxVal = 36;
                const widthPercent = (act.count / maxVal) * 100;

                return (
                  <div key={act.label} className="group cursor-pointer">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-700 font-medium group-hover:text-black transition-colors">
                        {act.label}
                      </span>
                      <span className="text-[11px] font-mono text-gray-400 group-hover:text-gray-900 transition-colors">
                        {activityMode === 'Volume' ? act.count : act.density}
                      </span>
                    </div>

                    <div className="h-3.5 w-full rounded-xs bg-gray-100 overflow-hidden">
                      <div
                        style={{ width: `${widthPercent}%` }}
                        className={`h-full rounded-xs ${act.color} transition-all duration-700 ease-out group-hover:brightness-110`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* X Axis scale */}
          <div className="mt-6 flex justify-between border-t border-gray-100 pt-2 text-[10px] text-gray-400 font-mono">
            <span>0</span>
            <span>9</span>
            <span>18</span>
            <span>27</span>
            <span>36</span>
          </div>
        </div>
      </div>

      {/* Bottom Section: Ranked Sites Table */}
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-gray-900">
            Sites ranked by SIF precursor density
          </h2>
          <span className="text-xs text-gray-400">14 sites monitored</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-gray-100 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
              <tr>
                <th className="pb-3 w-10">#</th>
                <th className="pb-3">Site</th>
                <th className="pb-3">Reports</th>
                <th className="pb-3">SIF Potential</th>
                <th className="pb-3 w-48">Density</th>
                <th className="pb-3 text-center">Trend</th>
                <th className="pb-3 text-right">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {siteRankings.map((row) => (
                <tr
                  key={row.rank}
                  className="hover:bg-gray-50/80 transition-colors cursor-pointer"
                >
                  <td className="py-3 text-gray-400 font-mono">{row.rank}</td>
                  <td className="py-3 font-semibold text-gray-900">{row.name}</td>
                  <td className="py-3 text-gray-600 font-mono">{row.reports}</td>
                  <td className="py-3 font-bold text-[#dc2626] font-mono">
                    {row.sif}
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-1.5 w-24 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          style={{ width: `${(row.densityVal / 35) * 100}%` }}
                          className={`h-full rounded-full ${
                            row.risk === 'HIGH'
                              ? 'bg-[#dc2626]'
                              : row.risk === 'REVIEW'
                              ? 'bg-[#f59e0b]'
                              : 'bg-[#10b981]'
                          }`}
                        />
                      </div>
                      <span className="font-mono text-gray-600 text-[11px]">
                        {row.density}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 text-center">
                    {row.trend === 'up' && (
                      <span className="inline-flex text-[#dc2626]">
                        <TrendingUp size={14} />
                      </span>
                    )}
                    {row.trend === 'down' && (
                      <span className="inline-flex text-[#10b981]">
                        <TrendingDown size={14} />
                      </span>
                    )}
                    {row.trend === 'neutral' && (
                      <span className="inline-flex text-gray-400">
                        <Minus size={14} />
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-right">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wider ${
                        row.risk === 'HIGH'
                          ? 'bg-red-50 text-[#dc2626] border border-red-200'
                          : row.risk === 'REVIEW'
                          ? 'bg-amber-50 text-[#d97706] border border-amber-200'
                          : 'bg-emerald-50 text-[#059669] border border-emerald-200'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          row.risk === 'HIGH'
                            ? 'bg-[#dc2626]'
                            : row.risk === 'REVIEW'
                            ? 'bg-[#d97706]'
                            : 'bg-[#059669]'
                        }`}
                      />
                      {row.risk}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}