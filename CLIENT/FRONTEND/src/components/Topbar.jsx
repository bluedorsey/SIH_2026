import React, { useState, useRef, useEffect } from 'react';
import { 
  Menu, 
  RefreshCw, 
  ChevronDown, 
  CheckCircle2, 
  Calendar, 
  MapPin, 
  Activity,
  Sparkles,
  ShieldAlert,
  ChevronRight
} from 'lucide-react';

export default function Topbar({ onOpenSidebar, pageTitle = 'Home' }) {
  const [dateDropdownOpen, setDateDropdownOpen] = useState(false);
  const [siteDropdownOpen, setSiteDropdownOpen] = useState(false);
  const [selectedDateRange, setSelectedDateRange] = useState('Last 30 days');
  const [selectedSite, setSelectedSite] = useState('All Sites');

  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncText, setLastSyncText] = useState('Updated 2 min ago');

  const [showStatusModal, setShowStatusModal] = useState(false);

  const dateRef = useRef(null);
  const siteRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (dateRef.current && !dateRef.current.contains(e.target)) {
        setDateDropdownOpen(false);
      }
      if (siteRef.current && !siteRef.current.contains(e.target)) {
        setSiteDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

 
  const handleManualSync = () => {
    if (isSyncing) return;
    setIsSyncing(true);
    setLastSyncText('Syncing telemetry...');
    setTimeout(() => {
      setIsSyncing(false);
      setLastSyncText('Updated just now');
    }, 1200);
  };

  const dateOptions = [
    'Today',
    'This week',
    'Last 30 days',
    'Last 90 days',
    'Quarter to date',
    'Year to date'
  ];

  const siteOptions = [
    'All Sites',
    'Duliajan',
    'Digboi',
    'Naharkatiya',
    'Moran',
    'Baghjan',
    'Rajasthan (Jodhpur)',
    'KG Basin'
  ];

  return (
    <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between border-b border-slate-200/90 bg-white/80 backdrop-blur-xl px-6 py-3.5 shadow-sm transition-all duration-300">

      <div className="flex items-center gap-4">
        <button
          onClick={onOpenSidebar}
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200/80 bg-slate-50/50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-300 active:scale-95 transition-all lg:hidden cursor-pointer shadow-2xs"
          aria-label="Open sidebar"
        >
          <Menu size={20} />
        </button>

        <nav aria-label="Breadcrumb" className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-linear-to-r from-teal-900 to-slate-900 text-teal-300 border border-teal-800/50 shadow-xs">
            <Sparkles size={13} className="text-teal-400 animate-pulse" />
            <span className="font-extrabold tracking-wider uppercase text-[11px]">
              OIL HSSE
            </span>
          </div>
          
          <ChevronRight size={15} className="text-slate-400 font-light" />
          
          <span className="font-bold text-slate-900 tracking-tight text-base sm:text-lg capitalize drop-shadow-xs">
            {pageTitle}
          </span>
        </nav>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        
        <button
          onClick={handleManualSync}
          disabled={isSyncing}
          className="group flex items-center gap-2 rounded-xl border border-slate-200/90 bg-slate-50/80 px-3.5 py-1.5 text-slate-600 hover:border-teal-300 hover:bg-teal-50/50 hover:text-teal-900 active:scale-95 transition-all duration-200 cursor-pointer shadow-2xs"
          title="Click to fetch live updates"
        >
          <RefreshCw
            size={15}
            className={`text-slate-400 group-hover:text-teal-600 transition-transform ${
              isSyncing ? 'animate-spin text-teal-600' : 'group-hover:rotate-180 duration-500'
            }`}
          />
          <span className="font-semibold text-xs select-none">
            {lastSyncText}
          </span>
        </button>

        <div className="relative">
          <button
            onMouseEnter={() => setShowStatusModal(true)}
            onMouseLeave={() => setShowStatusModal(false)}
            onClick={() => setShowStatusModal(!showStatusModal)}
            className="flex items-center gap-2.5 rounded-xl border border-emerald-300/80 bg-linear-to-r from-emerald-50 to-teal-50/60 px-3 py-1.5 text-xs font-bold text-emerald-950 shadow-2xs hover:shadow-xs hover:border-emerald-400 transition-all cursor-pointer"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-600 shadow-xs" />
            </span>
            <span>All Systems Operational</span>
          </button>

          {showStatusModal && (
            <div className="absolute right-0 top-full mt-2.5 w-64 rounded-2xl border border-slate-200/90 bg-white/95 backdrop-blur-md p-4 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-2.5 text-xs font-extrabold text-slate-900">
                <Activity size={16} className="text-emerald-600" />
                <span>Live Telemetry Status</span>
              </div>
              <div className="mt-3 space-y-2 text-xs text-slate-600">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-medium">NLP Engine:</span>
                  <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/60">Healthy (28ms)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-medium">Database:</span>
                  <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/60">Replicated</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-medium">Edge Telemetry:</span>
                  <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/60">Active Sync</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="relative" ref={dateRef}>
          <button
            type="button"
            onClick={() => {
              setDateDropdownOpen(!dateDropdownOpen);
              setSiteDropdownOpen(false);
            }}
            className={`flex items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-bold transition-all duration-200 cursor-pointer shadow-2xs ${
              dateDropdownOpen
                ? 'border-teal-600 bg-teal-500/10 text-teal-950 ring-2 ring-teal-500/20 shadow-xs'
                : 'border-slate-200/90 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50/80 hover:text-slate-900'
            }`}
          >
            <Calendar size={15} className={dateDropdownOpen ? 'text-teal-700' : 'text-slate-400'} />
            <span className="text-[13px]">{selectedDateRange}</span>
            <ChevronDown
              size={15}
              className={`text-slate-400 transition-transform duration-200 ${
                dateDropdownOpen ? 'rotate-180 text-teal-700' : ''
              }`}
            />
          </button>

          {dateDropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 rounded-2xl border border-slate-200/90 bg-white p-1.5 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-400 border-b border-slate-100 mb-1">
                Filter Duration
              </div>
              {dateOptions.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => {
                    setSelectedDateRange(opt);
                    setDateDropdownOpen(false);
                  }}
                  className={`flex w-full items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer ${
                    selectedDateRange === opt
                      ? 'bg-linear-to-r from-teal-50 to-emerald-50 text-teal-950 font-bold'
                      : 'text-slate-700 hover:bg-slate-100/70 hover:text-slate-900'
                  }`}
                >
                  <span>{opt}</span>
                  {selectedDateRange === opt && (
                    <CheckCircle2 size={15} className="text-teal-600 shrink-0" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
 
        <div className="relative" ref={siteRef}>
          <button
            type="button"
            onClick={() => {
              setSiteDropdownOpen(!siteDropdownOpen);
              setDateDropdownOpen(false);
            }}
            className={`flex items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-bold transition-all duration-200 cursor-pointer shadow-2xs ${
              siteDropdownOpen
                ? 'border-teal-600 bg-teal-500/10 text-teal-950 ring-2 ring-teal-500/20 shadow-xs'
                : 'border-slate-200/90 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50/80 hover:text-slate-900'
            }`}
          >
            <MapPin size={15} className={siteDropdownOpen ? 'text-teal-700' : 'text-slate-400'} />
            <span className="text-[13px]">{selectedSite}</span>
            <ChevronDown
              size={15}
              className={`text-slate-400 transition-transform duration-200 ${
                siteDropdownOpen ? 'rotate-180 text-teal-700' : ''
              }`}
            />
          </button>

          {siteDropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-52 rounded-2xl border border-slate-200/90 bg-white p-1.5 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-150 max-h-64 overflow-y-auto">
              <div className="px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-400 border-b border-slate-100 mb-1">
                Operational Site
              </div>
              {siteOptions.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => {
                    setSelectedSite(opt);
                    setSiteDropdownOpen(false);
                  }}
                  className={`flex w-full items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer ${
                    selectedSite === opt
                      ? 'bg-linear-to-r from-teal-50 to-emerald-50 text-teal-950 font-bold'
                      : 'text-slate-700 hover:bg-slate-100/70 hover:text-slate-900'
                  }`}
                >
                  <span className="truncate">{opt}</span>
                  {selectedSite === opt && (
                    <CheckCircle2 size={15} className="text-teal-600 shrink-0" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

      </div>
    </header>
  );
}