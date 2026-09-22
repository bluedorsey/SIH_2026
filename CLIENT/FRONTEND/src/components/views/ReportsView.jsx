import React, { useState, useMemo } from 'react';
import { 
  FileText, 
  Download, 
  Search, 
  Filter, 
  Calendar, 
  FileCheck, 
  Clock, 
  Plus, 
  CheckCircle2, 
  X, 
  Sparkles,
  BarChart2,
  ArrowUpRight,
  ChevronRight,
  FileSearch
} from 'lucide-react';

export default function ReportsView() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedFormat, setSelectedFormat] = useState('PDF');
  const [selectedScope, setSelectedScope] = useState('Full Corporate HSSE Executive Summary');
  const [selectedDateRange, setSelectedDateRange] = useState('Last 30 Days');
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  const reportStats = [
    { 
      title: 'Generated Reports', 
      value: '24', 
      detail: 'This month', 
      icon: FileText,
      accent: 'from-emerald-500 to-teal-700',
    },
    { 
      title: 'Scheduled Exports', 
      value: '04', 
      detail: 'Automated weekly', 
      icon: Calendar,
      accent: 'from-teal-600 to-cyan-700',
    },
    { 
      title: 'Compliance Audits', 
      value: '100%', 
      detail: 'Up to date', 
      icon: FileCheck,
      accent: 'from-slate-700 to-slate-900',
    },
    { 
      title: 'Avg. Generation Time', 
      value: '1.2s', 
      detail: 'Powered by AI Engine', 
      icon: Sparkles,
      accent: 'from-emerald-600 to-emerald-900',
    },
  ];

  const reportsList = [
    {
      id: 'REP-2026-089',
      title: 'Monthly SIF Precursor & Barrier Analysis',
      category: 'Safety Analytics',
      generatedDate: 'Sep 18, 2026',
      author: 'HSE Administrator',
      format: 'PDF',
      size: '2.4 MB',
      status: 'Ready'
    },
    {
      id: 'REP-2026-088',
      title: 'Duliajan Field Spatial Hazard Risk Audit',
      category: 'Site Intelligence',
      generatedDate: 'Sep 15, 2026',
      author: 'AI Automation',
      format: 'XLSX',
      size: '4.1 MB',
      status: 'Ready'
    },
    {
      id: 'REP-2026-084',
      title: 'Life-Saving Rules Compliance Telemetry',
      category: 'Compliance',
      generatedDate: 'Sep 10, 2026',
      author: 'HSE Administrator',
      format: 'PDF',
      size: '1.8 MB',
      status: 'Ready'
    },
    {
      id: 'REP-2026-079',
      title: 'Quarterly High-Risk Precursor Pattern Cluster Summary',
      category: 'Safety Analytics',
      generatedDate: 'Sep 01, 2026',
      author: 'AI Automation',
      format: 'PDF',
      size: '5.6 MB',
      status: 'Ready'
    },
    {
      id: 'REP-2026-072',
      title: 'Moran Station Atmospheric & Gas Drift Log',
      category: 'Site Intelligence',
      generatedDate: 'Aug 25, 2026',
      author: 'Field Safety Officer',
      format: 'CSV',
      size: '950 KB',
      status: 'Ready'
    }
  ];

  const filteredReports = useMemo(() => {
    return reportsList.filter((report) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch = 
        report.title.toLowerCase().includes(term) ||
        report.id.toLowerCase().includes(term) ||
        report.author.toLowerCase().includes(term);
      
      const matchesCategory = 
        selectedCategory === 'all' || 
        report.category.toLowerCase() === selectedCategory.toLowerCase();

      return matchesSearch && matchesCategory;
    });
  }, [searchTerm, selectedCategory]);

  const showToast = (message) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(''), 3000);
  };

  const handleDownload = (id, title) => {
    setDownloadingId(id);
    setTimeout(() => {
      setDownloadingId(null);
      showToast(`Successfully exported ${title}`);
    }, 1200);
  };

  const handleGenerateReport = () => {
    setIsGenerateModalOpen(false);
    showToast(`Generating ${selectedFormat} report for "${selectedScope}"...`);
  };

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

  return (
    <div className="p-6 space-y-6 bg-[#f8fafc] min-h-screen text-slate-800">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-xl border border-slate-700 text-xs font-semibold transition-all">
          <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

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
              Generate, schedule, and download real-time HSSE safety compliance summaries, SIF precursor metrics, and site risk logs.
            </p>
          </div>

          <button
            onClick={() => setIsGenerateModalOpen(true)}
            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 text-slate-950 text-xs font-bold hover:bg-emerald-400 shadow-sm transition-all duration-200 transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer shrink-0"
          >
            <Plus size={16} strokeWidth={2.5} />
            Generate New Report
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {reportStats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div 
              key={idx} 
              className="group bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs hover:shadow-md hover:border-slate-300 transition-all duration-200 flex items-center justify-between relative overflow-hidden"
            >
              <div className="space-y-1">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{stat.title}</p>
                <h3 className="text-2xl font-black text-slate-900">{stat.value}</h3>
                <p className="text-[11px] font-medium text-slate-500">{stat.detail}</p>
              </div>

              <div className={`p-3 rounded-xl bg-linear-to-br ${stat.accent} text-white shadow-xs group-hover:scale-105 transition-transform duration-200`}>
                <Icon size={20} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search report ID, title, or author..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#013531]/20 focus:border-[#013531] transition-all"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-semibold">
            <Filter size={14} className="text-slate-400" />
            <span>Category:</span>
          </div>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50/50 font-medium text-slate-700 focus:outline-none focus:border-[#013531] focus:ring-2 focus:ring-[#013531]/10 cursor-pointer transition-all"
          >
            <option value="all">All Categories</option>
            <option value="safety analytics">Safety Analytics</option>
            <option value="site intelligence">Site Intelligence</option>
            <option value="compliance">Compliance</option>
          </select>
        </div>
      </div>

      {/* Reports Table Card */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-5">Report Document</th>
                <th className="py-3.5 px-4">Category</th>
                <th className="py-3.5 px-4">Generated Date</th>
                <th className="py-3.5 px-4">Author / Source</th>
                <th className="py-3.5 px-4 text-center">Format</th>
                <th className="py-3.5 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredReports.length > 0 ? (
                filteredReports.map((report) => (
                  <tr 
                    key={report.id} 
                    className="group hover:bg-slate-50/80 transition-colors duration-150"
                  >
                    <td className="py-4 px-5">
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-lg bg-teal-50 text-[#013531] border border-teal-100 group-hover:bg-[#013531] group-hover:text-white transition-colors duration-200">
                          <BarChart2 size={16} />
                        </div>
                        <div className="space-y-0.5">
                          <span className="text-[10px] font-mono font-bold text-slate-400 group-hover:text-slate-500 transition-colors">
                            {report.id}
                          </span>
                          <h4 className="font-bold text-slate-900 group-hover:text-[#013531] flex items-center gap-1 transition-colors">
                            {report.title}
                            <ArrowUpRight size={13} className="opacity-0 group-hover:opacity-100 text-[#013531] transition-opacity" />
                          </h4>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 font-semibold text-slate-600">
                      <span className="px-2.5 py-1 rounded-md bg-slate-100/80 text-slate-700 border border-slate-200/80 text-[11px]">
                        {report.category}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-slate-500 font-medium">
                      <div className="flex items-center gap-1.5">
                        <Clock size={13} className="text-slate-400" />
                        <span>{report.generatedDate}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4 font-semibold text-slate-700">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {report.author}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <span className={`inline-block font-bold text-[10px] px-2.5 py-1 rounded-md border transition-colors ${getFormatBadgeStyle(report.format)}`}>
                        {report.format} • {report.size}
                      </span>
                    </td>
                    <td className="py-4 px-5 text-right">
                      <button
                        onClick={() => handleDownload(report.id, report.title)}
                        disabled={downloadingId === report.id}
                        className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#013531] text-white font-semibold text-xs hover:bg-[#002724] disabled:opacity-50 transition-all duration-150 shadow-xs active:scale-95 cursor-pointer"
                      >
                        <Download size={13} />
                        <span>{downloadingId === report.id ? 'Downloading...' : 'Export'}</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <FileSearch size={32} className="text-slate-300" />
                      <p className="font-semibold text-sm">No reports found</p>
                      <p className="text-xs text-slate-400">Try adjusting your search criteria or category filters.</p>
                      <button 
                        onClick={() => { setSearchTerm(''); setSelectedCategory('all'); }} 
                        className="mt-2 text-xs font-bold text-[#013531] underline hover:text-[#002724]"
                      >
                        Reset filters
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Custom Report Modal */}
      {isGenerateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-5 relative">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-teal-50 text-[#013531]">
                  <Sparkles size={16} />
                </div>
                <h3 className="text-base font-bold text-slate-900">Custom Report Generator</h3>
              </div>
              <button 
                onClick={() => setIsGenerateModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1.5">Report Scope</label>
                <select 
                  value={selectedScope}
                  onChange={(e) => setSelectedScope(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 font-medium text-slate-800 focus:outline-none focus:border-[#013531] focus:ring-2 focus:ring-[#013531]/10"
                >
                  <option>Full Corporate HSSE Executive Summary</option>
                  <option>SIF-Precursor Risk Breakdown</option>
                  <option>Site Spatial Barrier Analysis (Duliajan/Digboi)</option>
                  <option>Life-Saving Rules Non-Compliance Log</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1.5">Date Range</label>
                <select 
                  value={selectedDateRange}
                  onChange={(e) => setSelectedDateRange(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 font-medium text-slate-800 focus:outline-none focus:border-[#013531] focus:ring-2 focus:ring-[#013531]/10"
                >
                  <option>Last 30 Days</option>
                  <option>Current Quarter (Q3 2026)</option>
                  <option>Year to Date (2026)</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1.5">Export Format</label>
                <div className="grid grid-cols-3 gap-2.5">
                  {['PDF', 'Excel (.xlsx)', 'CSV'].map((fmt) => {
                    const isSelected = selectedFormat === fmt;
                    return (
                      <button 
                        key={fmt}
                        type="button" 
                        onClick={() => setSelectedFormat(fmt)}
                        className={`py-2 px-3 font-bold rounded-xl border text-xs transition-all duration-150 cursor-pointer ${
                          isSelected
                            ? 'border-[#013531] bg-[#013531] text-white shadow-xs'
                            : 'border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
                        }`}
                      >
                        {fmt}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end gap-2.5 border-t border-slate-100">
              <button
                onClick={() => setIsGenerateModalOpen(false)}
                className="px-4 py-2.5 text-xs font-semibold rounded-xl bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateReport}
                className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold rounded-xl bg-[#013531] text-white hover:bg-[#002724] shadow-xs transition-all cursor-pointer"
              >
                <span>Compile & Download</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}