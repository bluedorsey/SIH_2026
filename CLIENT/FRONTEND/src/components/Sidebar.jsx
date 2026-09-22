import React from 'react';
import {
  Home,
  FileSearch,
  Layers,
  BarChart3,
  Network,
  MapPin,
  ShieldCheck,
  FileText,
  Server,
  Settings,
  Zap,
  X,
  Bell
} from 'lucide-react';

export default function Sidebar({ isOpen, onClose, activeTab, setActiveTab }) {
 
  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'analyse', label: 'Analyse Statement', icon: FileSearch },
    { id: 'triage', label: 'SIF-Precursor ', icon: Layers,},
    { id: 'risk-dashboard', label: 'Risk Dashboard', icon: BarChart3 },
    { id: 'patterns', label: 'Precursor Patterns', icon: Network },
    { id: 'sites', label: 'Sites & Activities', icon: MapPin },
    { id: 'rules', label: 'Life-Saving Rules', icon: ShieldCheck },
    { id: 'reports', label: 'Reports', icon: FileText },
  ];

  const bottomNavItems = [
    { id: 'system', label: 'System', icon: Server },
    { id: 'admin', label: 'Administration', icon: Settings },
  ];

  const handleNavClick = (id) => {
    setActiveTab(id);
    if (onClose) onClose(); 
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#013531] text-[#93a7a4] transition-transform duration-300 ease-in-out lg:sticky lg:top-0 lg:h-screen lg:shrink-0 lg:translate-x-0 overflow-y-auto ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <div className="flex items-center gap-3">
            <img
              src="/logo.png"
              alt="OIL Logo"
              className="h-8 w-auto object-contain"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className="text-xl font-bold tracking-tight text-white">
              OIL HSSE
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-white lg:hidden cursor-pointer"
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-left cursor-pointer ${
                  isActive
                    ? 'bg-[#004e47] text-white border border-[#0b635c]'
                    : 'text-[#8da5a1] hover:bg-[#08423d] hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon size={18} className={isActive ? 'text-[#14b8a6]' : ''} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#eb3d3d] text-[11px] font-bold text-white">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div className="my-4 border-t border-[#0d443f]" />

          
          {bottomNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-left cursor-pointer ${
                  isActive
                    ? 'bg-[#004e47] text-white'
                    : 'text-[#8da5a1] hover:bg-[#08423d] hover:text-white'
                }`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="p-3">
          <div className="rounded-xl bg-[#002724] p-3.5 border border-[#0d4742]/50">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#10b981]">
              <Zap size={14} />
              <span>AI Model Status</span>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-xs text-white">
              <span className="h-2 w-2 rounded-full bg-[#10b981]" />
              <span className="font-medium">Model operational</span>
            </div>
            <p className="mt-0.5 text-[11px] text-[#6d8a86]">
              NLP v3.2 · Sync 2m ago
            </p>
          </div>
        </div>

        
        <div 
          className={`flex items-center justify-between border-t border-[#093f3a] p-3.5 transition-colors duration-150 cursor-pointer ${
            activeTab === 'hse-admin' 
              ? 'bg-[#004e47] border-l-4 border-l-[#14b8a6]' 
              : 'bg-[#002e2b] hover:bg-[#003834]'
          }`}
          onClick={() => handleNavClick('hse-admin')}
          title="Open HSE Administration Profile"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#ea580c] text-xs font-bold text-white shadow-xs">
              HA
            </div>
            <div className="truncate">
              <p className="text-xs font-semibold text-white leading-tight truncate">
                HSE Administrator
              </p>
              <p className="text-[10px] text-[#71928e] truncate">OIL Corporate HSSE</p>
            </div>
          </div>
          <div 
            className="relative shrink-0 p-1 rounded-md hover:bg-white/10 transition-colors"
            onClick={(e) => {
              e.stopPropagation(); 
            }}
          >
            <Bell size={18} className="text-[#84a39f] hover:text-white cursor-pointer" />
            {/* <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#ea580c] text-[9px] font-bold text-white">
              4
            </span> */}
          </div>
        </div>
      </aside>
    </>
  );
}