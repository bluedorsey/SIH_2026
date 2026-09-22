import React, { useState } from 'react';
import { 
  ShieldCheck, 
  AlertOctagon, 
  Search, 
  Filter, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Info,
  ChevronRight,
  TrendingDown
} from 'lucide-react';

export default function LifeSavingRulesView() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCompliance, setSelectedCompliance] = useState('all');
  const [activeRuleModal, setActiveRuleModal] = useState(null);

  const summaryStats = [
    { title: 'Total Rules Tracked', value: '09 Rules', detail: 'OIL HSSE Framework', color: 'text-slate-900' },
    { title: 'Avg. Compliance Rate', value: '91.8%', detail: '+1.2% vs last month', color: 'text-emerald-600' },
    { title: 'Total Breaches', value: '18 Active', detail: 'Requires intervention', color: 'text-rose-600' },
    { title: 'Highest Risk Area', value: 'Bypassing Isolation', detail: '8 recorded bypasses', color: 'text-amber-600' },
  ];

  const rules = [
    {
      id: 'LSR-01',
      title: 'Bypassing Safety Controls / Isolation',
      category: 'Energy Isolation (LOTO)',
      complianceRate: 82,
      breachesCount: 8,
      nearMissesCount: 14,
      status: 'High Risk',
      mandatoryActions: [
        'Obtain authorization before overriding safety controls.',
        'Verify zero energy state before work begins.',
        'Apply locks and tags at all isolation points.'
      ],
      description: 'Breaches related to unauthorized bypass of lockout/tagout procedures during live operations.'
    },
    {
      id: 'LSR-02',
      title: 'Confined Space Entry',
      category: 'Hazardous Atmosphere',
      complianceRate: 94,
      breachesCount: 2,
      nearMissesCount: 5,
      status: 'Compliant',
      mandatoryActions: [
        'Test gas levels prior to entry and continuously monitor.',
        'Confirm standby person is stationed outside.',
        'Verify emergency rescue plan is active.'
      ],
      description: 'Strict adherence to atmospheric testing and entry permits before entering tanks or pits.'
    },
    {
      id: 'LSR-03',
      title: 'Working at Height',
      category: 'Fall Protection',
      complianceRate: 88,
      breachesCount: 5,
      nearMissesCount: 11,
      status: 'Attention Needed',
      mandatoryActions: [
        'Inspect fall protection equipment before use.',
        '100% tie-off required above 1.8 meters.',
        'Ensure proper scaffolding inspection tag is valid.'
      ],
      description: 'Failures involving unanchored harnesses, missing toe-boards, or damaged scaffolding locks.'
    },
    {
      id: 'LSR-04',
      title: 'Safe Mechanical Lifting',
      category: 'Lifting Operations',
      complianceRate: 96,
      breachesCount: 1,
      nearMissesCount: 3,
      status: 'Compliant',
      mandatoryActions: [
        'Do not walk under a suspended load.',
        'Verify crane operator and rigger certification.',
        'Ensure lift plan is approved for heavy/critical lifts.'
      ],
      description: 'Protocol governing rigged loads, exclusion zone integrity, and crane stability checks.'
    },
    {
      id: 'LSR-05',
      title: 'Hot Work in Explosive Atmospheres',
      category: 'Fire & Explosion',
      complianceRate: 91,
      breachesCount: 2,
      nearMissesCount: 6,
      status: 'Compliant',
      mandatoryActions: [
        'Obtain valid Hot Work Permit before ignition.',
        'Conduct continuous flammable gas monitoring.',
        'Clear combustible materials within 10m radius.'
      ],
      description: 'Welding, grinding, or cutting activities performed near hydrocarbons or pressurized lines.'
    }
  ];

  const filteredRules = rules.filter((rule) => {
    const matchesSearch = rule.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          rule.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          rule.category.toLowerCase().includes(searchTerm.toLowerCase());
    
    let matchesFilter = true;
    if (selectedCompliance === 'high-risk') matchesFilter = rule.status === 'High Risk';
    if (selectedCompliance === 'attention') matchesFilter = rule.status === 'Attention Needed';
    if (selectedCompliance === 'compliant') matchesFilter = rule.status === 'Compliant';

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="p-6 space-y-6 bg-[#f3f6f9] min-h-screen text-slate-800">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <ShieldCheck className="text-[#013531]" size={26} />
            Life-Saving Rules Compliance
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time telemetry and observations tracking core safety barrier adherence across all field sites.
          </p>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryStats.map((stat, idx) => (
          <div key={idx} className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{stat.title}</p>
            <h3 className={`text-2xl font-black mt-1 ${stat.color}`}>{stat.value}</h3>
            <p className="text-[11px] font-medium text-slate-500 mt-0.5">{stat.detail}</p>
          </div>
        ))}
      </div>

      {/* Search and Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search rule name, ID, or category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#013531]/20 focus:border-[#013531]"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
            <Filter size={14} />
            <span>Filter Status:</span>
          </div>
          <select
            value={selectedCompliance}
            onChange={(e) => setSelectedCompliance(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 font-medium text-slate-700 focus:outline-none focus:border-[#013531] cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="high-risk">High Risk Only</option>
            <option value="attention">Attention Needed</option>
            <option value="compliant">Compliant</option>
          </select>
        </div>
      </div>

      {/* Life Saving Rules List / Grid */}
      <div className="space-y-4">
        {filteredRules.map((rule) => (
          <div 
            key={rule.id}
            className="bg-white p-5 rounded-xl border border-slate-200/90 shadow-xs hover:border-[#013531]/40 transition"
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              
              {/* Left Column - Rule Title & Metadata */}
              <div className="space-y-1 max-w-xl">
                <div className="flex items-center gap-2.5">
                  <span className="text-xs font-black text-slate-400 tracking-wider">{rule.id}</span>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                    {rule.category}
                  </span>
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                    rule.status === 'High Risk'
                      ? 'bg-rose-100 text-rose-700 border-rose-200'
                      : rule.status === 'Attention Needed'
                      ? 'bg-amber-100 text-amber-800 border-amber-200'
                      : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                  }`}>
                    {rule.status}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900">{rule.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{rule.description}</p>
              </div>

              {/* Middle Column - Compliance Meter & Counts */}
              <div className="flex items-center gap-6 border-y lg:border-y-0 lg:border-x border-slate-100 py-3 lg:py-0 lg:px-6">
                <div>
                  <div className="flex items-center justify-between gap-3 text-xs mb-1">
                    <span className="font-semibold text-slate-600">Compliance Rate</span>
                    <span className="font-black text-slate-900">{rule.complianceRate}%</span>
                  </div>
                  <div className="w-36 h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${
                        rule.complianceRate < 85 ? 'bg-rose-500' : rule.complianceRate < 92 ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${rule.complianceRate}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs">
                  <div className="text-center">
                    <span className="block text-sm font-black text-rose-600">{rule.breachesCount}</span>
                    <span className="text-[10px] text-slate-400 font-medium uppercase">Breaches</span>
                  </div>
                  <div className="text-center">
                    <span className="block text-sm font-black text-amber-600">{rule.nearMissesCount}</span>
                    <span className="text-[10px] text-slate-400 font-medium uppercase">Near Misses</span>
                  </div>
                </div>
              </div>

              {/* Right Column - Action Button */}
              <div>
                <button
                  onClick={() => setActiveRuleModal(rule)}
                  className="w-full lg:w-auto flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-[#013531] text-white hover:bg-[#002724] transition shadow-2xs cursor-pointer"
                >
                  <span>Rule Protocol</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Protocol Modal */}
      {activeRuleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4 relative">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-bold text-slate-400">{activeRuleModal.id} Protocol</span>
                <h3 className="text-base font-bold text-slate-900">{activeRuleModal.title}</h3>
              </div>
              <button
                onClick={() => setActiveRuleModal(null)}
                className="text-slate-400 hover:text-slate-700 text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">Mandatory Controls:</p>
              <ul className="space-y-2 text-xs text-slate-600">
                {activeRuleModal.mandatoryActions.map((action, i) => (
                  <li key={i} className="flex items-start gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <CheckCircle2 size={15} className="text-emerald-600 mt-0.5 shrink-0" />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setActiveRuleModal(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer"
              >
                Close Protocol
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}