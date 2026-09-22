import React, { useState } from 'react';
import { 
  Cpu, 
  Database, 
  Activity, 
  Server, 
  Edit3, 
  Save, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  FileCode, 
  Download, 
  ShieldAlert, 
  Sliders, 
  Zap,
  Check,
  Radio,
  Copy,
  X,
  Filter,
  ArrowUpRight
} from 'lucide-react';

export default function SystemView() {
  const [toastMessage, setToastMessage] = useState('');
  const [isEditingThresholds, setIsEditingThresholds] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFilter, setSyncFilter] = useState('all'); // 'all', 'connected', 'pending'
  const [isYamlModalOpen, setIsYamlModalOpen] = useState(false);

  // Model Specifications Data
  const modelsList = [
    {
      component: 'Rule engine',
      model: 'policy_table_v4.yaml',
      role: 'Deterministic triage',
      version: '4.2',
      size: '0.4 MB',
      quantisation: '—',
      latency: '< 1 ms',
      status: 'active'
    },
    {
      component: 'Fast classifier',
      model: 'muril-base-cased',
      role: 'SIF / Exposure label',
      version: '1.0.0',
      size: '471 MB',
      quantisation: 'INT8',
      latency: '42 ms',
      status: 'active'
    },
    {
      component: 'Extractor',
      model: 'xlm-r-token-tagger',
      role: 'Energy span extraction',
      version: '2.3.1',
      size: '1.1 GB',
      quantisation: 'INT8',
      latency: '118 ms',
      status: 'active'
    },
    {
      component: 'Reader',
      model: 'qwen2.5-3b-instruct',
      role: 'Uncertain-lane detail',
      version: '2.5.0',
      size: '3.1 GB',
      quantisation: 'Q4_K',
      latency: '2.4 s',
      status: 'active'
    },
    {
      component: 'Language ID',
      model: 'fasttext-lid-176',
      role: 'Language detection',
      version: '0.9.2',
      size: '0.9 MB',
      quantisation: '—',
      latency: '< 1 ms',
      status: 'active'
    }
  ];

  // Editable Energy Thresholds Data
  const [thresholds, setThresholds] = useState([
    { category: 'Dropped object', value: 40, source: 'DROPS calculator v3', lastEdited: '12 Aug 2026' },
    { category: 'Fall from height', value: 300, source: 'Energy-threshold policy v4', lastEdited: '12 Aug 2026' },
    { category: 'Mobile equipment / motion', value: 1200, source: 'Vehicle impact model', lastEdited: '01 Sep 2026' },
    { category: 'Pressure release', value: 500, source: 'Process safety review', lastEdited: '02 Sep 2026' },
    { category: 'Electrical', value: 50, source: 'IEC 60479-1', lastEdited: '12 Aug 2026' }
  ]);

  // Sync Topology Data
  const [syncSites, setSyncSites] = useState([
    { name: 'Duliajan', role: 'HUB', timeAgo: '2 min ago', status: 'connected' },
    { name: 'Moran', role: '', timeAgo: '4 min ago', status: 'connected' },
    { name: 'Naharkatiya', role: '', timeAgo: '6 min ago', status: 'connected' },
    { name: 'KG Basin', role: '', timeAgo: '18 min ago', status: 'pending' },
    { name: 'Jorhat', role: '', timeAgo: '7 min ago', status: 'connected' },
    { name: 'Baghjan', role: '', timeAgo: '11 min ago', status: 'connected' },
    { name: 'Rajasthan (Jodhpur)', role: '', timeAgo: '34 min ago', status: 'pending' }
  ]);

  const evaluationMetrics = [
    { label: 'Recall · P-SIF', value: 0.94, percent: 94, color: 'bg-emerald-500' },
    { label: 'Recall · H-SIF', value: 0.91, percent: 91, color: 'bg-emerald-500' },
    { label: 'Recall · Exposure', value: 0.88, percent: 88, color: 'bg-emerald-500' },
    { label: 'Span F1 · energy source', value: 0.86, percent: 86, color: 'bg-emerald-500' },
    { label: 'Span F1 · release', value: 0.83, percent: 83, color: 'bg-amber-500' },
    { label: 'Span F1 · person in path', value: 0.79, percent: 79, color: 'bg-amber-500' },
    { label: 'Span F1 · control', value: 0.71, percent: 71, color: 'bg-rose-500', isWeakest: true },
  ];

  const [yamlConfig, setYamlConfig] = useState(`sites:
  duliajan:
    default_height_m: 2.0
    default_mass_kg: 25
    default_pressure_kPa: 700
    energy_model: drops_v3
  baghjan:
    default_height_m: 3.5
    default_mass_kg: 40
    default_pressure_kPa: 1100
    energy_model: drops_v3
  kg_basin:
    default_height_m: 4.0
    default_mass_kg: 60
    default_pressure_kPa: 2200
    energy_model: process_v2
  moran:
    default_height_m: 2.5
    default_mass_kg: 30
    default_pressure_kPa: 850
    energy_model: drops_v3`);

  const [tempYaml, setTempYaml] = useState(yamlConfig);

  const handleThresholdChange = (index, newValue) => {
    const updated = [...thresholds];
    updated[index].value = Number(newValue) || 0;
    updated[index].lastEdited = 'Just now';
    setThresholds(updated);
  };

  const handleSaveThresholds = () => {
    setIsEditingThresholds(false);
    showToast('Energy thresholds saved successfully.');
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3200);
  };

  const handleRefreshSync = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
      setSyncSites((prev) =>
        prev.map((site) => ({ ...site, timeAgo: 'Just now' }))
      );
      showToast('Sync topology refreshed successfully.');
    }, 1200);
  };

  const handleCopyYaml = () => {
    navigator.clipboard.writeText(yamlConfig);
    showToast('YAML configuration copied to clipboard.');
  };

  const handleSaveYaml = () => {
    setYamlConfig(tempYaml);
    setIsYamlModalOpen(false);
    showToast('site_defaults.yaml configuration updated.');
  };

  const filteredSyncSites = syncSites.filter((site) => {
    if (syncFilter === 'connected') return site.status === 'connected';
    if (syncFilter === 'pending') return site.status === 'pending';
    return true;
  });

  return (
    <div className="p-6 space-y-6 bg-[#f8fafc] min-h-screen text-slate-800 relative">
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-2xl border border-slate-700 text-xs font-semibold animate-in fade-in slide-in-from-bottom-4 duration-200">
          <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {isYamlModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-2xl overflow-hidden animate-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <FileCode size={18} className="text-[#013531]" />
                <h3 className="text-sm font-bold text-slate-900">Edit site_defaults.yaml</h3>
              </div>
              <button
                onClick={() => setIsYamlModalOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-200/60 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-4 bg-slate-950">
              <textarea
                value={tempYaml}
                onChange={(e) => setTempYaml(e.target.value)}
                rows={12}
                className="w-full bg-transparent font-mono text-xs text-emerald-400 focus:outline-none resize-none leading-relaxed"
              />
            </div>
            <div className="p-4 border-t border-slate-100 flex items-center justify-end gap-2 bg-slate-50/50">
              <button
                onClick={() => setIsYamlModalOpen(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 font-semibold text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveYaml}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#013531] text-white font-bold text-xs hover:bg-[#024a44] transition-colors cursor-pointer shadow-xs"
              >
                <Save size={13} />
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium mb-1">
            <span>OIL HSSE</span>
            <span>/</span>
            <span className="text-slate-900 font-bold">System</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            System Operational Architecture & AI Models
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200/80 font-mono font-medium">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>Offline · 06:40 · 3 pending</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 font-medium shadow-2xs">
            <Radio size={13} className="text-emerald-600" />
            <span>Light Field</span>
          </div>

          <button 
            onClick={() => showToast('System operational status exported (JSON).')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-semibold hover:bg-slate-100 active:scale-95 transition-all cursor-pointer shadow-2xs"
          >
            <Download size={13} />
            <span>Export</span>
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200/80 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>State: Live</span>
          </div>
        </div>
      </div>

      {/* Panel 1: AI Models Pipeline */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-[#013531] text-white">
              <Cpu size={18} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Models Architecture</h2>
              <p className="text-[11px] font-mono text-slate-500">
                run mode CPU, fully offline · 16 GB RAM host
              </p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-md bg-emerald-100/80 text-emerald-800 text-[10px] font-bold border border-emerald-200 uppercase tracking-wider self-start sm:self-auto flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            All Systems Operational
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200/80 bg-slate-50/80 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-5">Component</th>
                <th className="py-3 px-4">Model Name</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Quantisation</th>
                <th className="py-3 px-5 text-right">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {modelsList.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors group">
                  <td className="py-3.5 px-5 font-bold text-slate-900">{row.component}</td>
                  <td className="py-3.5 px-4 font-mono text-[#013531] font-semibold group-hover:text-emerald-700 transition-colors">
                    {row.model}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">{row.role}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-500">{row.version}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-500">{row.size}</td>
                  <td className="py-3.5 px-4">
                    {row.quantisation !== '—' ? (
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px] font-bold border border-slate-200">
                        {row.quantisation}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                  <td className="py-3.5 px-5 text-right font-mono font-bold text-emerald-700">{row.latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/80 shadow-2xs flex flex-col">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-[#013531]" />
              <h2 className="text-sm font-bold text-slate-900">Energy thresholds</h2>
              <span className="text-xs text-slate-400 font-mono">— editable</span>
            </div>
            
            {isEditingThresholds ? (
              <button
                onClick={handleSaveThresholds}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold text-xs hover:bg-emerald-700 active:scale-95 transition-all cursor-pointer shadow-2xs"
              >
                <Save size={13} />
                <span>Save</span>
              </button>
            ) : (
              <button
                onClick={() => setIsEditingThresholds(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 font-bold text-xs hover:bg-slate-200 active:scale-95 transition-all cursor-pointer"
              >
                <Edit3 size={13} />
                <span>Edit</span>
              </button>
            )}
          </div>

          <div className="p-4 overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="pb-2.5">Category</th>
                  <th className="pb-2.5 text-center">Threshold (J)</th>
                  <th className="pb-2.5">Source</th>
                  <th className="pb-2.5 text-right">Last Edited</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {thresholds.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 font-semibold text-slate-800">{item.category}</td>
                    <td className="py-3 text-center">
                      {isEditingThresholds ? (
                        <input
                          type="number"
                          value={item.value}
                          onChange={(e) => handleThresholdChange(idx, e.target.value)}
                          className="w-20 px-2 py-1 text-center font-mono font-bold text-xs border border-emerald-500 rounded focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-emerald-50/30 transition-all"
                        />
                      ) : (
                        <span className="px-3 py-1 rounded bg-slate-100 font-mono font-bold text-slate-900 border border-slate-200/60 inline-block min-w-[60px]">
                          {item.value}
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-slate-500 font-medium">{item.source}</td>
                    <td className="py-3 text-right text-slate-400 font-mono text-[11px]">{item.lastEdited}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200/80 shadow-2xs flex flex-col">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCode size={16} className="text-[#013531]" />
              <h2 className="text-sm font-mono font-bold text-slate-900">site_defaults.yaml</h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyYaml}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold transition-colors cursor-pointer"
                title="Copy YAML"
              >
                <Copy size={12} />
                <span>Copy</span>
              </button>
              <button
                onClick={() => {
                  setTempYaml(yamlConfig);
                  setIsYamlModalOpen(true);
                }}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#013531] hover:bg-[#024a44] text-white text-[11px] font-semibold transition-colors cursor-pointer"
              >
                <Edit3 size={12} />
                <span>Edit Code</span>
              </button>
            </div>
          </div>

          <div className="p-4 bg-slate-900 text-emerald-400 font-mono text-xs leading-relaxed overflow-x-auto rounded-b-xl flex-1 max-h-[310px] overflow-y-auto">
            <pre className="text-slate-300">
              <code>{yamlConfig}</code>
            </pre>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Panel 4: Sync Topology */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200/80 shadow-2xs p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Sync topology</h2>
                <p className="text-[11px] font-mono text-slate-400">hub: central Postgres, Duliajan</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRefreshSync}
                  disabled={isSyncing}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition-all cursor-pointer disabled:opacity-50"
                  title="Refresh topology"
                >
                  <RefreshCw size={14} className={isSyncing ? 'animate-spin text-emerald-600' : ''} />
                </button>
                <Server size={18} className="text-slate-400" />
              </div>
            </div>

            {/* Filter Chips */}
            <div className="flex items-center gap-1.5 mb-3 text-[11px]">
              <span className="text-slate-400 font-medium flex items-center gap-1 mr-1">
                <Filter size={11} />
                Filter:
              </span>
              {['all', 'connected', 'pending'].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setSyncFilter(filter)}
                  className={`px-2.5 py-0.5 rounded-md font-semibold capitalize transition-all cursor-pointer ${
                    syncFilter === filter
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>

            <div className="space-y-2.5 max-h-[280px] overflow-y-auto pr-1">
              {filteredSyncSites.map((site, idx) => (
                <div 
                  key={idx} 
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-100/80 transition-colors text-xs"
                >
                  <div className="flex items-center gap-2.5 font-semibold text-slate-800">
                    <span className={`w-2 h-2 rounded-full ${site.status === 'connected' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
                    <span>{site.name}</span>
                    {site.role && (
                      <span className="px-1.5 py-0.5 text-[9px] font-bold font-mono bg-slate-200 text-slate-700 rounded uppercase">
                        {site.role}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 font-mono text-[11px]">{site.timeAgo}</span>
                    <span className={`font-bold text-[11px] capitalize ${site.status === 'connected' ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {site.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Panel 5: Last Evaluation Performance Metrics */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Last evaluation</h2>
                <p className="text-[11px] font-mono text-slate-400">02 Sep 2026 · 1,842 held-out reports</p>
              </div>
              <Activity size={18} className="text-[#013531]" />
            </div>

            <div className="space-y-3.5">
              {evaluationMetrics.map((metric, idx) => (
                <div key={idx} className="space-y-1 group">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-700 group-hover:text-slate-900 transition-colors">{metric.label}</span>
                    <span className="font-mono text-slate-900 font-bold">{metric.value.toFixed(2)}</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${metric.color}`}
                      style={{ width: `${metric.percent}%` }}
                    />
                  </div>
                  {metric.isWeakest && (
                    <p className="text-[10px] text-rose-600 font-medium italic mt-0.5">
                      weakest — drives most overrides
                    </p>
                  )}
                </div>
              ))}

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-700">Human override rate 30d</span>
                <span className="font-mono text-amber-700 font-bold">8.4%</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2">
            <p className="text-[11px] text-slate-400 italic max-w-sm">
              Honest numbers. Span F1 on control is the weakest link and drives most overrides.
            </p>
            <button 
              onClick={() => showToast('Downloading Weekly Brief PDF...')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 text-white font-bold text-xs hover:bg-slate-800 active:scale-95 transition-all cursor-pointer shrink-0 shadow-2xs"
            >
              <Download size={13} />
              <span>Weekly brief → PDF</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}