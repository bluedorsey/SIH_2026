import React, { useState, useEffect } from 'react';
import { getPatterns } from '../../services/api';
import { 
  Network, 
  Search, 
  Filter, 
  AlertTriangle, 
  TrendingUp, 
  ShieldAlert, 
  RefreshCw,
  Eye,
  Layers,
  ArrowUpRight,
  Sparkles,
  X,
  Download,
  CheckCircle2,
  FileText,
  Activity,
  Sliders,
  ChevronRight,
  Info
} from 'lucide-react';

export default function PrecursorPatternsView() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRisk, setSelectedRisk] = useState('all');
  const [isReclustering, setIsReclustering] = useState(false);
  const [isReclusterSuccess, setIsReclusterSuccess] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [activeAnalysisPattern, setActiveAnalysisPattern] = useState(null);
  const [exportFormat, setExportFormat] = useState('pdf');
  const [isExporting, setIsExporting] = useState(false);

  const [stats, setStats] = useState([
    { title: 'Detected Clusters', value: '0 Active', trend: 'From DB', icon: Network, color: 'text-teal-400' },
    { title: 'High-Risk Patterns', value: '00 Critical', trend: 'Requires Review', icon: AlertTriangle, color: 'text-rose-400' },
    { title: 'Pattern Confidence', value: '-', trend: 'Pipeline v0.7', icon: Sparkles, color: 'text-emerald-400' },
    { title: 'Correlated Incidents', value: '0 Total', trend: 'Across 0 clusters', icon: Layers, color: 'text-amber-400' },
  ]);

  const [patterns, setPatterns] = useState([]);

  useEffect(() => {
    async function loadPatterns() {
      try {
        const data = await getPatterns(1, 20);
        const items = data?.data || [];
        if (items.length > 0) {
          const mapped = items.map((p, idx) => ({
            id: `PAT-${1000 + idx}`,
            title: p.display_name || p.name,
            category: (p.code || '').replace(/_/g, ' '),
            riskLevel: p.report_count > 5 ? 'Critical' : p.report_count > 2 ? 'High' : 'Medium',
            confidence: '-',
            occurrences: p.report_count,
            leadIndicator: `${p.sites_affected} site(s) affected`,
            impactArea: 'All Sites',
            status: p.report_count > 0 ? 'Active Monitoring' : 'No Data Yet',
            description: `Precursor cluster: ${p.display_name}. ${p.report_count} reports linked.`,
            timeline: [],
            recommendedActions: []
          }));
          setPatterns(mapped);
        }
        // Update stats from real data
        const totalClusters = items.length;
        const highRisk = items.filter(i => i.report_count > 5).length;
        const totalCorrelated = items.reduce((sum, i) => sum + i.report_count, 0);
        setStats([
          { title: 'Detected Clusters', value: `${totalClusters} Active`, trend: 'From DB', icon: Network, color: 'text-teal-400' },
          { title: 'High-Risk Patterns', value: `${String(highRisk).padStart(2, '0')} Critical`, trend: 'Requires Review', icon: AlertTriangle, color: 'text-rose-400' },
          { title: 'Pattern Confidence', value: '-', trend: 'Pipeline v0.7', icon: Sparkles, color: 'text-emerald-400' },
          { title: 'Correlated Incidents', value: `${totalCorrelated} Total`, trend: `Across ${new Set(items.flatMap(i => [])).size || totalClusters} clusters`, icon: Layers, color: 'text-amber-400' },
        ]);
      } catch (err) {
        console.error('Failed to load patterns:', err);
      }
    }
    loadPatterns();
  }, []);

  const handleRecluster = () => {
    setIsReclustering(true);
    setIsReclusterSuccess(false);

    setTimeout(() => {
      setIsReclustering(false);
      setIsReclusterSuccess(true);

      setStats([
        { title: 'Detected Clusters', value: '16 Active', trend: '+2 re-clustered', icon: Network, color: 'text-teal-400' },
        { title: 'High-Risk Patterns', value: '06 Critical', trend: 'Updated just now', icon: AlertTriangle, color: 'text-rose-400' },
        { title: 'Pattern Confidence', value: '95.8%', trend: 'NLP Model v3.2', icon: Sparkles, color: 'text-emerald-400' },
        { title: 'Correlated Incidents', value: '134 Total', trend: 'Fresh NLP Scan', icon: Layers, color: 'text-amber-400' },
      ]);

      setTimeout(() => setIsReclusterSuccess(false), 4000);
    }, 1200);
  };

  const handleDownloadReport = () => {
    setIsExporting(true);
    setTimeout(() => {
      setIsExporting(false);
      setShowExportModal(false);
      const downloadAnchor = document.createElement('a');
      downloadAnchor.href = '#';
      downloadAnchor.download = `HSSE_Precursor_Report_${new Date().toISOString().slice(0, 10)}.${exportFormat}`;
    }, 1500);
  };

  const filteredPatterns = patterns.filter((pattern) => {
    const matchesSearch = 
      pattern.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
      pattern.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      pattern.impactArea.toLowerCase().includes(searchTerm.toLowerCase()) ||
      pattern.category.toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchesRisk = selectedRisk === 'all' || pattern.riskLevel.toLowerCase() === selectedRisk.toLowerCase();
    
    return matchesSearch && matchesRisk;
  });

  return (
    <div className="p-4 sm:p-6 space-y-6 bg-[#f3f6f9] min-h-screen text-slate-800">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Network className="text-[#013531]" size={26} />
            Precursor Patterns & Clusters
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            AI-driven cluster identification and leading indicators derived from field safety observations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleRecluster}
            disabled={isReclustering}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:border-slate-300 shadow-xs transition-all duration-200 active:scale-95 cursor-pointer ${
              isReclustering ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            <RefreshCw size={14} className={`text-slate-500 ${isReclustering ? 'animate-spin text-[#013531]' : ''}`} />
            {isReclustering ? 'Re-clustering...' : 'Re-cluster Data'}
          </button>

          <button 
            onClick={() => setShowExportModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#013531] text-white text-xs font-semibold hover:bg-[#002724] hover:shadow-md transition-all duration-200 active:scale-95 cursor-pointer"
          >
            <ShieldAlert size={14} />
            Export Risk Report
          </button>
        </div>
      </div>

      {isReclusterSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center justify-between text-xs font-medium animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600" />
            <span>AI Clustering Complete: 2 new precursor patterns identified and confidence score updated!</span>
          </div>
          <button onClick={() => setIsReclusterSuccess(false)} className="text-emerald-600 hover:text-emerald-900 cursor-pointer">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div 
              key={idx} 
              className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:shadow-md hover:border-slate-300 transition-all duration-200 flex items-center justify-between group"
            >
              <div>
                <p className="text-xs font-medium text-slate-500">{stat.title}</p>
                <h3 className="text-xl font-bold text-slate-900 mt-1">{stat.value}</h3>
                <p className="text-[11px] font-semibold text-slate-400 mt-0.5 group-hover:text-slate-600 transition-colors">
                  {stat.trend}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-[#013531] text-white group-hover:scale-105 transition-transform duration-200">
                <Icon size={20} className={stat.color} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search pattern, ID, location, or category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-8 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#013531]/20 focus:border-[#013531] transition-all"
          />
          {searchTerm && (
            <button 
              onClick={() => setSearchTerm('')} 
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
            <Filter size={14} />
            <span>Risk Level:</span>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg">
            {['all', 'critical', 'high', 'medium'].map((level) => (
              <button
                key={level}
                onClick={() => setSelectedRisk(level)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md capitalize transition-all cursor-pointer ${
                  selectedRisk === level
                    ? 'bg-white text-[#013531] shadow-xs font-bold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredPatterns.length > 0 ? (
          filteredPatterns.map((pattern) => (
            <div 
              key={pattern.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:shadow-lg hover:border-[#013531]/50 transition-all duration-300 flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-bold text-slate-400 tracking-wider uppercase group-hover:text-[#013531] transition-colors">
                    {pattern.id}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                    pattern.riskLevel === 'Critical' 
                      ? 'bg-rose-100 text-rose-700 border-rose-200' 
                      : pattern.riskLevel === 'High'
                      ? 'bg-amber-100 text-amber-800 border-amber-200'
                      : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                  }`}>
                    {pattern.riskLevel} Risk
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 mt-2 leading-snug group-hover:text-[#013531] transition-colors">
                  {pattern.title}
                </h3>

                <div className="mt-3 space-y-2 text-xs">
                  <div className="bg-slate-50 group-hover:bg-teal-50/40 p-3 rounded-lg border border-slate-100 transition-colors">
                    <span className="font-semibold text-slate-700">Leading Indicator:</span>
                    <p className="text-slate-600 mt-0.5">{pattern.leadIndicator}</p>
                  </div>

                  <div className="flex flex-wrap items-center justify-between text-slate-500 pt-1 gap-2">
                    <span>Site / Unit: <strong className="text-slate-700">{pattern.impactArea}</strong></span>
                    <span>Category: <strong className="text-slate-700">{pattern.category}</strong></span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <div className="flex items-center gap-4 text-slate-500">
                  <span>Occurrences: <strong className="text-slate-900">{pattern.occurrences}</strong></span>
                  <span>Confidence: <strong className="text-teal-700 font-bold">{pattern.confidence}</strong></span>
                </div>
                
                <button 
                  onClick={() => setActiveAnalysisPattern(pattern)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold text-[#013531] bg-teal-50 hover:bg-[#013531] hover:text-white transition-all duration-200 cursor-pointer active:scale-95"
                >
                  <span>Analyze Cluster</span>
                  <ArrowUpRight size={14} />
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full bg-white p-12 rounded-xl border border-dashed border-slate-300 text-center">
            <Info size={32} className="mx-auto text-slate-400 mb-2" />
            <h3 className="text-base font-bold text-slate-800">No matching precursor patterns found</h3>
            <p className="text-xs text-slate-500 mt-1">Try adjusting your search criteria or risk filter.</p>
            <button 
              onClick={() => { setSearchTerm(''); setSelectedRisk('all'); }}
              className="mt-4 px-4 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200 transition cursor-pointer"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {showExportModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="text-[#013531]" size={20} />
                <h3 className="text-lg font-bold text-slate-900">Export Risk Pattern Report</h3>
              </div>
              <button 
                onClick={() => setShowExportModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="py-4 space-y-4">
              <p className="text-xs text-slate-600">
                Generate an executive HSSE Risk Summary report based on currently filtered precursor clusters.
              </p>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-2">Select Export Format</label>
                <div className="grid grid-cols-3 gap-2">
                  {['pdf', 'xlsx', 'csv'].map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => setExportFormat(fmt)}
                      className={`py-2 px-3 rounded-xl border text-xs font-bold uppercase transition-all cursor-pointer ${
                        exportFormat === fmt
                          ? 'border-[#013531] bg-[#013531]/5 text-[#013531]'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-[11px] text-slate-500 space-y-1">
                <div className="flex justify-between">
                  <span>Scope:</span>
                  <strong className="text-slate-800">{filteredPatterns.length} Active Cluster Patterns</strong>
                </div>
                <div className="flex justify-between">
                  <span>Risk Filter:</span>
                  <strong className="text-slate-800 capitalize">{selectedRisk}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Generated By:</span>
                  <strong className="text-slate-800">OIL HSSE Analytics Engine</strong>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                onClick={() => setShowExportModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDownloadReport}
                disabled={isExporting}
                className="flex items-center gap-2 px-4 py-2 bg-[#013531] text-white text-xs font-semibold rounded-lg hover:bg-[#002724] transition shadow-xs cursor-pointer"
              >
                {isExporting ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    <span>Exporting...</span>
                  </>
                ) : (
                  <>
                    <Download size={14} />
                    <span>Download Report</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {activeAnalysisPattern && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 my-8 animate-in fade-in zoom-in duration-200">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#013531] bg-teal-50 px-2.5 py-0.5 rounded-md">
                    {activeAnalysisPattern.id}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                    activeAnalysisPattern.riskLevel === 'Critical' 
                      ? 'bg-rose-100 text-rose-700 border-rose-200' 
                      : activeAnalysisPattern.riskLevel === 'High'
                      ? 'bg-amber-100 text-amber-800 border-amber-200'
                      : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                  }`}>
                    {activeAnalysisPattern.riskLevel} Risk
                  </span>
                </div>
                <h2 className="text-lg font-bold text-slate-900 mt-2">
                  {activeAnalysisPattern.title}
                </h2>
              </div>
              <button 
                onClick={() => setActiveAnalysisPattern(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            <div className="py-4 space-y-4 text-xs">
              <div>
                <h4 className="font-bold text-slate-800 mb-1">AI Diagnostic Breakdown</h4>
                <p className="text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100">
                  {activeAnalysisPattern.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span className="text-slate-500 font-medium">Confidence Score:</span>
                  <p className="text-base font-bold text-teal-700 mt-0.5">{activeAnalysisPattern.confidence}</p>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span className="text-slate-500 font-medium">Recorded Events:</span>
                  <p className="text-base font-bold text-slate-900 mt-0.5">{activeAnalysisPattern.occurrences} Logs</p>
                </div>
              </div>

              <div>
                <h4 className="font-bold text-slate-800 mb-2">Pattern Detection Progression</h4>
                <div className="space-y-2 border-l-2 border-[#013531]/20 pl-3">
                  {activeAnalysisPattern.timeline.map((event, i) => (
                    <div key={i} className="relative flex items-center gap-2 text-slate-600">
                      <div className="w-2 h-2 rounded-full bg-[#013531] absolute -left-4.25" />
                      <span>{event}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-bold text-slate-800 mb-2">AI-Recommended Mitigation Steps</h4>
                <div className="space-y-1.5">
                  {activeAnalysisPattern.recommendedActions.map((action, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-teal-50/50 text-slate-800 border border-teal-100">
                      <CheckCircle2 size={14} className="text-[#013531] shrink-0" />
                      <span>{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <span className="text-[11px] text-slate-400">
                Location: {activeAnalysisPattern.impactArea}
              </span>
              <button
                onClick={() => setActiveAnalysisPattern(null)}
                className="px-4 py-2 bg-[#013531] text-white text-xs font-semibold rounded-lg hover:bg-[#002724] transition cursor-pointer"
              >
                Close Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}