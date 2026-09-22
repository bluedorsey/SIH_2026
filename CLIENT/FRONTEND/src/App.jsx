import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import HomeView from './components/views/HomeView';
import AnalyseStatementView from './components/views/AnalyseStatementView';
import SifPrecursorTriageView from './components/views/SifPrecursorTriageView';
import RiskDashboardView from './components/views/RiskDashboardView';
import PrecursorPatternsView from './components/views/PrecursorPatternsView';
import SitesActivitiesView from './components/views/SitesActivitiesView';
import LifeSavingRulesView from './components/views/LifeSavingRulesView';
import ReportsView from './components/views/ReportsView';
import SystemView from './components/views/SystemView';
import AdminView from './components/views/AdminView';
import HseAdminProfileView from './components/views/HseAdminProfileView';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
   
  const [activeTab, setActiveTab] = useState('home');

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
  };

  const getPageTitle = (tab) => {
    switch (tab) {
      case 'risk-dashboard': return 'Risk Dashboard';
      case 'triage': return 'SIF-Precursor Triage';
      case 'analyse': return 'Analyse Statement';
      case 'patterns': return 'Precursor Patterns';
      case 'sites': return 'Sites & Activities';
      case 'rules': return 'Life-Saving Rules';
      case 'reports': return 'Reports';
      case 'system': return 'System';
      case 'admin': return 'Administration';
      case 'hse-admin': return 'HSE Administration Profile';
      default: return tab.replace('-', ' ');
    }
  };

  return (
    <div className="flex min-h-screen bg-[#f3f6f9] text-[#1c2a38] font-sans antialiased">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeTab={activeTab}
        setActiveTab={handleTabChange}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          onOpenSidebar={() => setSidebarOpen(true)}
          pageTitle={getPageTitle(activeTab)}
        />

        {activeTab === 'home' && <HomeView onNavigate={(tabId) => handleTabChange(tabId)} />}
        {activeTab === 'analyse' && <AnalyseStatementView />}
        {activeTab === 'triage' && <SifPrecursorTriageView />}
        {activeTab === 'risk-dashboard' && <RiskDashboardView />}
        {activeTab === 'patterns' && <PrecursorPatternsView />}
        {activeTab === 'sites' && <SitesActivitiesView />}
        {activeTab === 'rules' && <LifeSavingRulesView />}
        {activeTab === 'reports' && <ReportsView />}
        {activeTab === 'system' && <SystemView />}
        {activeTab === 'admin' && <AdminView />}
        {activeTab === 'hse-admin' && <HseAdminProfileView />}
      </div>
    </div>
  );
}