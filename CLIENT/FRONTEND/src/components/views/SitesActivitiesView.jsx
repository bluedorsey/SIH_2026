import React, { useState, useEffect } from 'react';
import { RefreshCw, ChevronDown, MapPin, Activity, ShieldAlert, Image as ImageIcon } from 'lucide-react';
import { getSites } from '../../services/api';

export default function SitesActivitiesView() {
  const [sites, setSites] = useState([]);
  const [selectedSite, setSelectedSite] = useState('Duliajan');
  const [selectedTimeRange, setSelectedTimeRange] = useState('Last 30 days');
  const [activeSiteFilter, setActiveSiteFilter] = useState('All Sites');
  const [activeZoneNode, setActiveZoneNode] = useState(null);

  useEffect(() => {
    getSites(1, 100)
      .then(res => {
        if (res && res.data) {
          setSites(res.data);
          if (res.data.length > 0 && !res.data.some(s => (s.name || s.site_name) === 'Duliajan')) {
            setSelectedSite(res.data[0].name || res.data[0].site_name);
          }
        }
      })
      .catch(err => console.error("Error fetching sites:", err));
  }, []);

  // Placeholder zone data (no zone-level API yet)
  const zones = [
    { id: 'compressor', name: 'Compressor Area', count: 6, level: 'HIGH', badgeBg: 'bg-red-100 text-red-600 border-red-200', nodeColor: 'bg-red-500 text-white ring-4 ring-red-500/30', x: '58%', y: '18%' },
    { id: 'wellhead', name: 'Wellhead', count: 4, level: 'HIGH', badgeBg: 'bg-red-100 text-red-600 border-red-200', nodeColor: 'bg-red-500 text-white ring-4 ring-red-500/30', x: '78%', y: '35%' },
    { id: 'processing', name: 'Processing Unit', count: 3, level: 'REVIEW', badgeBg: 'bg-amber-100 text-amber-600 border-amber-200', nodeColor: 'bg-amber-400 text-slate-900 ring-4 ring-amber-400/30', x: '68%', y: '73%' },
    { id: 'workshop', name: 'Workshop', count: 1, level: 'ROUTINE', badgeBg: 'bg-emerald-100 text-emerald-600 border-emerald-200', nodeColor: 'bg-emerald-500 text-white ring-4 ring-emerald-500/30', x: '53%', y: '73%' },
    { id: 'storage', name: 'Storage Area', count: 1, level: 'ROUTINE', badgeBg: 'bg-emerald-100 text-emerald-600 border-emerald-200', nodeColor: 'bg-emerald-500 text-white ring-4 ring-emerald-500/30', x: '81%', y: '81%' },
  ];

  const totalObs = sites.length > 0 ? sites.reduce((acc, curr) => acc + (curr.total_reports || 0), 0) : 184;
  const totalSif = sites.length > 0 ? sites.reduce((acc, curr) => acc + (curr.sif_count || 0), 0) : 52;

  const siteKPIs = [
    { label: 'Total observations', value: totalObs },
    { label: 'SIF-potential', value: totalSif },
    { label: 'Near misses', value: 31 },
    { label: 'Critical barriers failed', value: 8 },
    { label: 'Open actions', value: 14 },
  ];

  return (
    <div className="p-6 space-y-6 bg-slate-100 min-h-screen text-slate-800 font-sans">
      
      <div className="relative h-48 sm:h-56 w-full rounded-2xl overflow-hidden shadow-sm border border-slate-200">
        <img 
          src="/1.jpg" 
          alt="Site Operations Banner" 
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-950/90 via-emerald-950/40 to-transparent p-6 flex flex-col justify-end">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-200 border border-emerald-500/30 backdrop-blur-sm w-fit mb-2">
            <MapPin size={14} />
            <span>Active Industrial Field Ops</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            {selectedSite} Onshore Field Surveillance
          </h2>
          <p className="text-sm text-emerald-100/80 max-w-xl mt-1">
            Real-time environmental monitoring, hazard tracking, and live telemetry feed.
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Site Intelligence</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Spatial precursor concentration and site risk analytics
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-500 mr-1">
            <RefreshCw size={14} className="text-slate-400" />
            <span>Updated 2 min ago</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 ml-1"></span>
            <span className="text-slate-600 font-medium">All systems operational</span>
          </div>

          <div className="relative">
            <select
              value={selectedTimeRange}
              onChange={(e) => setSelectedTimeRange(e.target.value)}
              className="appearance-none bg-white border border-slate-200 rounded-lg px-3 py-2 pr-8 font-medium text-slate-700 shadow-sm hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 cursor-pointer"
            >
              <option>Last 30 days</option>
              <option>Last 7 days</option>
              <option>Last 90 days</option>
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={activeSiteFilter}
              onChange={(e) => setActiveSiteFilter(e.target.value)}
              className="appearance-none bg-white border border-slate-200 rounded-lg px-3 py-2 pr-8 font-medium text-slate-700 shadow-sm hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 cursor-pointer"
            >
              <option>All Sites</option>
              <option>Duliajan Field</option>
              <option>Digboi Refinery</option>
              <option>Moran Station</option>
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={selectedSite}
              onChange={(e) => setSelectedSite(e.target.value)}
              className="appearance-none bg-emerald-900 text-white font-medium rounded-lg px-3.5 py-2 pr-8 shadow-sm hover:bg-emerald-950 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 cursor-pointer"
            >
              {sites.length > 0 ? (
                sites.map(site => (
                  <option key={site.site_code || site.name} value={site.name || site.site_name}>
                    Site: {site.name || site.site_name}
                  </option>
                ))
              ) : (
                <>
                  <option value="Duliajan">Site: Duliajan</option>
                  <option value="Digboi">Site: Digboi</option>
                  <option value="Moran">Site: Moran</option>
                </>
              )}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-emerald-200 pointer-events-none" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <div className="lg:col-span-12 space-y-5">
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            
            <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between">
              <div className="flex items-center justify-between px-1 mb-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <ImageIcon size={14} />
                  Site Surveillance — {selectedSite}
                </span>
                <span className="text-[11px] font-semibold bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full border border-emerald-100">
                  Live Feed
                </span>
              </div>
              
              <div className="relative h-48 rounded-xl overflow-hidden border border-slate-100 group">
                <img 
                  src="/img2.jpg" 
                  alt="Site Activity Surveillance" 
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-linear-to-t from-black/80 via-transparent to-black/20 p-4 flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <span className="bg-red-600 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-sm">
                      HIGH RISK ZONE
                    </span>
                  </div>
                  <div className="text-white space-y-0.5">
                    <p className="text-xs font-bold leading-snug">{selectedSite} Processing Sector</p>
                    <p className="text-[11px] text-slate-300">Continuous hazard precursor monitoring active</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  SITE RISK SCORE
                </p>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-5xl font-black text-red-600 tracking-tight">78</span>
                  <span className="text-base font-semibold text-slate-400">/ 100</span>
                  <span className="ml-3 inline-flex items-center gap-1.5 text-xs font-bold text-red-600 bg-red-50 px-2.5 py-1 rounded-full border border-red-100">
                    <span className="h-2 w-2 rounded-full bg-red-600"></span> Elevated
                  </span>
                </div>
              </div>

              <div className="mt-6">
                <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full w-[78%] bg-gradient-to-r from-amber-500 to-red-600 rounded-full"></div>
                </div>
              </div>
            </div>

          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                SITE KPIS
              </p>
              <div className="space-y-3 text-xs">
                {siteKPIs.map((kpi, idx) => (
                  <div key={idx} className="flex items-center justify-between pb-2 border-b border-slate-100 last:border-0 last:pb-0">
                    <span className="text-slate-600 font-medium">{kpi.label}</span>
                    <span className="font-bold text-slate-900 text-sm">{kpi.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                ZONE BREAKDOWN
              </p>
              <div className="space-y-2">
                {zones.map((zone) => (
                  <div
                    key={zone.id}
                    onClick={() => setActiveZoneNode(zone.id)}
                    className={`flex items-center justify-between p-3 rounded-xl border text-xs cursor-pointer transition ${
                      activeZoneNode === zone.id
                        ? 'bg-slate-50 border-emerald-800 shadow-sm'
                        : 'border-slate-100 hover:bg-slate-50/80 hover:border-slate-200'
                    }`}
                  >
                    <span className="font-semibold text-slate-800">{zone.name}</span>
                    <div className="flex items-center gap-2.5">
                      <span className="font-bold text-slate-900">{zone.count} SIF</span>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${zone.badgeBg}`}>
                        {zone.level}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      </div>

      <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-lg flex flex-col h-[550px] relative mt-6">
        <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 backdrop-blur-md">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide">
              Site Risk Map — {selectedSite} Field
            </h2>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium text-slate-300">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block"></span> HIGH
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400 inline-block"></span> REVIEW
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block"></span> ROUTINE
            </span>
            <span className="text-slate-400 font-normal border-l border-slate-700 pl-3">
              Number = SIF-potential count
            </span>
          </div>
        </div>

        <div className="relative flex-1 bg-slate-950 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] overflow-hidden">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-700 text-xs font-medium text-emerald-400 shadow-md">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            LIVE · {selectedSite} Field
          </div>

          <svg className="absolute inset-0 w-full h-full pointer-events-none stroke-amber-500/30" strokeDasharray="6,6" strokeWidth="2">
            <line x1="58%" y1="22%" x2="78%" y2="38%" />
            <line x1="78%" y1="38%" x2="68%" y2="72%" />
            <line x1="68%" y1="72%" x2="53%" y2="72%" />
          </svg>

          <div
            className={`absolute top-[18%] left-[58%] -translate-x-1/2 p-3 rounded-xl border border-slate-800 bg-slate-900/90 backdrop-blur-sm flex items-center gap-3 cursor-pointer transition hover:scale-105 ${
              activeZoneNode === 'compressor' ? 'ring-2 ring-red-500 border-transparent' : ''
            }`}
            onClick={() => setActiveZoneNode('compressor')}
          >
            <span className="text-xs font-medium text-slate-200">Compressor</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white ring-4 ring-red-500/20">
              6
            </span>
          </div>

          <div
            className={`absolute top-[35%] left-[78%] -translate-x-1/2 p-3 rounded-xl border border-slate-800 bg-slate-900/90 backdrop-blur-sm flex items-center gap-3 cursor-pointer transition hover:scale-105 ${
              activeZoneNode === 'wellhead' ? 'ring-2 ring-red-500 border-transparent' : ''
            }`}
            onClick={() => setActiveZoneNode('wellhead')}
          >
            <span className="text-xs font-medium text-slate-200">Wellhead</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white ring-4 ring-red-500/20">
              4
            </span>
          </div>

          <div
            className={`absolute top-[73%] left-[68%] -translate-x-1/2 p-3 rounded-xl border border-slate-800 bg-slate-900/90 backdrop-blur-sm flex items-center gap-3 cursor-pointer transition hover:scale-105 ${
              activeZoneNode === 'processing' ? 'ring-2 ring-amber-400 border-transparent' : ''
            }`}
            onClick={() => setActiveZoneNode('processing')}
          >
            <span className="text-xs font-medium text-slate-200">Processing</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-400 text-xs font-bold text-slate-950 ring-4 ring-amber-400/20">
              3
            </span>
          </div>

          <div
            className={`absolute top-[73%] left-[53%] -translate-x-1/2 p-3 rounded-xl border border-slate-800 bg-slate-900/90 backdrop-blur-sm flex items-center gap-3 cursor-pointer transition hover:scale-105 ${
              activeZoneNode === 'workshop' ? 'ring-2 ring-emerald-500 border-transparent' : ''
            }`}
            onClick={() => setActiveZoneNode('workshop')}
          >
            <span className="text-xs font-medium text-slate-200">Workshop</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 text-xs font-bold text-white ring-4 ring-emerald-500/20">
              1
            </span>
          </div>

          <div
            className={`absolute top-[81%] left-[81%] -translate-x-1/2 p-3 rounded-xl border border-slate-800 bg-slate-900/90 backdrop-blur-sm flex items-center gap-3 cursor-pointer transition hover:scale-105 ${
              activeZoneNode === 'storage' ? 'ring-2 ring-emerald-500 border-transparent' : ''
            }`}
            onClick={() => setActiveZoneNode('storage')}
          >
            <span className="text-xs font-medium text-slate-200">Storage</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 text-xs font-bold text-white ring-4 ring-emerald-500/20">
              1
            </span>
          </div>
        </div>
      </div>

    </div>
  );
}