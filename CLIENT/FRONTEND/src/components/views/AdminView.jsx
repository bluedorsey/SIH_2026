import React, { useState } from 'react';
import {
  ShieldCheck,
  Users,
  Key,
  Server,
  Activity,
  Search,
  CheckCircle2,
  Eye,
  EyeOff,
  Download,
  Terminal,
  UserPlus,
  Cpu,
  Lock,
  ArrowUpRight,
  Sparkles
} from 'lucide-react';

export default function AdminView() {
  const [toastMessage, setToastMessage] = useState('');
  const [activeTab, setActiveTab] = useState('users'); // 'users', 'services', 'config', 'logs'
  const [searchTerm, setSearchTerm] = useState('');
  const [showSecrets, setShowSecrets] = useState(false);

  // Toast Trigger Helper
  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3000);
  };

  // Mock User List
  const [users, setUsers] = useState([
    { id: 1, name: 'Abhi Jais', email: 'abhi@oil.gov.in', role: 'System Admin', site: 'Duliajan Hub', status: 'Active', lastActive: 'Just now' },
    { id: 2, name: 'Rajesh Sharma', email: 'r.sharma@oil.gov.in', role: 'HSSE Officer', site: 'Moran', status: 'Active', lastActive: '12 min ago' },
    { id: 3, name: 'Priya Das', email: 'p.das@oil.gov.in', role: 'Operator', site: 'Naharkatiya', status: 'Active', lastActive: '1 hour ago' },
    { id: 4, name: 'Ankit Verma', email: 'a.verma@oil.gov.in', role: 'Auditor', site: 'KG Basin', status: 'Inactive', lastActive: '3 days ago' },
  ]);

  // System Services Status
  const [services] = useState([
    { name: 'PostgreSQL Core DB', endpoint: 'localhost:5432', latency: '2 ms', status: 'Healthy', uptime: '99.98%' },
    { name: 'Inference Engine (Qwen/MuRIL)', endpoint: '127.0.0.1:8080', latency: '42 ms', status: 'Healthy', uptime: '99.85%' },
    { name: 'Sync Broker (Redis Queue)', endpoint: 'localhost:6379', latency: '1 ms', status: 'Healthy', uptime: '100%' },
    { name: 'Offline Storage Sync Agent', endpoint: '10.0.4.12:9090', latency: '180 ms', status: 'Warning', uptime: '98.12%' },
  ]);

  // System Logs
  const [logs] = useState([
    { id: 'LOG-8821', time: '06:38:12', type: 'Config Change', user: 'Abhi Jais', detail: 'Updated threshold for Fall from height to 300J', level: 'info' },
    { id: 'LOG-8820', time: '06:15:00', type: 'Sync Event', user: 'System', detail: 'Site KG Basin sync delayed > 15 mins', level: 'warning' },
    { id: 'LOG-8819', time: '05:42:19', type: 'Security', user: 'Rajesh Sharma', detail: 'User session authenticated via local OTP', level: 'info' },
    { id: 'LOG-8818', time: '04:10:05', type: 'Model Triage', user: 'System', detail: 'High-energy span override logged by Operator', level: 'info' },
  ]);

  const toggleUserStatus = (id) => {
    setUsers(users.map(u => u.id === id ? { ...u, status: u.status === 'Active' ? 'Inactive' : 'Active' } : u));
    showToast('User status updated successfully.');
  };

  const activeUsersCount = users.filter(u => u.status === 'Active').length;
  const healthyServicesCount = services.filter(s => s.status === 'Healthy').length;

  return (
    <div className="p-6 space-y-6 bg-[#f8fafc] min-h-screen text-slate-800 relative font-sans">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-2xl border border-slate-700 text-xs font-semibold animate-in fade-in slide-in-from-bottom-4 duration-200">
          <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Breadcrumb */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
          <span>OIL HSSE</span>
          <span>/</span>
          <span className="text-slate-900 font-bold">Administration</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => showToast('Audit logs exported to CSV.')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200/80 text-slate-700 font-semibold text-xs hover:bg-slate-50 hover:border-slate-300 hover:shadow-xs active:scale-95 transition-all duration-150 cursor-pointer"
          >
            <Download size={13} className="text-slate-500" />
            <span>Export Logs</span>
          </button>
          <button
            onClick={() => showToast('User invite modal opened.')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#013531] text-white font-semibold text-xs hover:bg-[#024a44] hover:shadow-md hover:shadow-[#013531]/10 active:scale-95 transition-all duration-150 cursor-pointer"
          >
            <UserPlus size={13} />
            <span>Add User</span>
          </button>
        </div>
      </div>

      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#012d29] via-[#013531] to-[#044a44] p-6 text-white shadow-xl">
        {/* Subtle Decorative Background Shapes */}
        <div className="absolute -top-12 -right-12 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 w-64 h-64 bg-teal-400/10 rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-400/30 text-emerald-300 text-[11px] font-semibold backdrop-blur-md">
              <Sparkles size={12} className="text-emerald-400 animate-pulse" />
              <span>System Operational & Managed</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              System Settings & Access Control
            </h1>
            <p className="text-xs sm:text-sm text-emerald-100/80 leading-relaxed">
              Centralized administrative hub for access policies, database configuration, infrastructure health monitoring, and security audit logs.
            </p>
          </div>

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-3 gap-3 shrink-0">
            <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-xl p-3.5 hover:bg-white/15 transition-all group">
              <div className="flex items-center justify-between text-emerald-200/70 text-[10px] font-bold uppercase tracking-wider mb-1">
                <span>Active Users</span>
                <Users size={14} className="text-emerald-300 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xl font-extrabold text-white">{activeUsersCount} / {users.length}</div>
              <div className="text-[10px] text-emerald-300/80 mt-0.5">RBAC Active</div>
            </div>

            <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-xl p-3.5 hover:bg-white/15 transition-all group">
              <div className="flex items-center justify-between text-emerald-200/70 text-[10px] font-bold uppercase tracking-wider mb-1">
                <span>Services</span>
                <Cpu size={14} className="text-emerald-300 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xl font-extrabold text-white">{healthyServicesCount} / {services.length}</div>
              <div className="text-[10px] text-emerald-300/80 mt-0.5">99.8% avg uptime</div>
            </div>

            <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-xl p-3.5 hover:bg-white/15 transition-all group">
              <div className="flex items-center justify-between text-emerald-200/70 text-[10px] font-bold uppercase tracking-wider mb-1">
                <span>Audit Status</span>
                <Lock size={14} className="text-emerald-300 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xl font-extrabold text-white">Strict</div>
              <div className="text-[10px] text-emerald-300/80 mt-0.5">AES-256 Vault</div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1.5 bg-slate-200/70 p-1.5 rounded-xl w-fit text-xs font-bold border border-slate-200/60 shadow-2xs">
        {[
          { id: 'users', label: 'User & Access', icon: Users },
          { id: 'services', label: 'Service Health', icon: Server },
          { id: 'config', label: 'Environment Config', icon: Key },
          { id: 'logs', label: 'Audit Trail', icon: Terminal },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 cursor-pointer ${
                isActive
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/60 active:scale-95'
              }`}
            >
              <Icon size={14} className={isActive ? 'text-[#013531]' : 'text-slate-400'} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: USER MANAGEMENT */}
      {activeTab === 'users' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden transition-all">
          <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
            <div className="relative flex-1 max-w-xs">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search users or roles..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:outline-none focus:ring-2 focus:ring-[#013531]/20 focus:border-[#013531] transition-all"
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <ShieldCheck size={14} className="text-emerald-600" />
              <span>RBAC Policy: <strong className="text-slate-800">Enforced (Strict)</strong></span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200/80 bg-slate-50/80 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-5">User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Assigned Site</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Last Activity</th>
                  <th className="py-3 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                {users
                  .filter(u => u.name.toLowerCase().includes(searchTerm.toLowerCase()) || u.role.toLowerCase().includes(searchTerm.toLowerCase()))
                  .map((user) => (
                    <tr 
                      key={user.id} 
                      className="hover:bg-slate-50/80 hover:translate-x-0.5 transition-all duration-150"
                    >
                      <td className="py-3.5 px-5">
                        <div className="font-bold text-slate-900">{user.name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">{user.email}</div>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800">{user.role}</td>
                      <td className="py-3.5 px-4 text-slate-600">{user.site}</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border transition-colors ${
                          user.status === 'Active'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : 'bg-slate-100 text-slate-500 border-slate-200'
                        }`}>
                          {user.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">{user.lastActive}</td>
                      <td className="py-3.5 px-5 text-right">
                        <button
                          onClick={() => toggleUserStatus(user.id)}
                          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200/80 text-slate-700 text-[11px] font-semibold active:scale-95 transition-all cursor-pointer"
                        >
                          {user.status === 'Active' ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: SERVICE HEALTH */}
      {activeTab === 'services' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {services.map((svc, idx) => (
            <div 
              key={idx} 
              className="bg-white rounded-xl border border-slate-200/80 p-4 flex flex-col justify-between hover:shadow-md hover:border-slate-300 hover:-translate-y-0.5 transition-all duration-200"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    {svc.name}
                  </h3>
                  <span className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                    svc.status === 'Healthy' 
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200' 
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${svc.status === 'Healthy' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
                    {svc.status}
                  </span>
                </div>
                <p className="font-mono text-xs text-slate-400 mb-4 bg-slate-50 p-1.5 rounded border border-slate-100 w-fit">{svc.endpoint}</p>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400">Latency: </span>
                  <span className="font-mono font-bold text-slate-800">{svc.latency}</span>
                </div>
                <div>
                  <span className="text-slate-400">Uptime: </span>
                  <span className="font-mono font-bold text-slate-800">{svc.uptime}</span>
                </div>
                <button 
                  onClick={() => showToast(`Pinging ${svc.name}...`)}
                  className="text-[#013531] hover:text-[#024a44] font-bold flex items-center gap-1 hover:underline cursor-pointer transition-colors"
                >
                  <span>Ping</span>
                  <ArrowUpRight size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'config' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Environment Secrets & Endpoints</h2>
              <p className="text-xs text-slate-400">System level variables stored in local encrypted vault.</p>
            </div>
            <button
              onClick={() => setShowSecrets(!showSecrets)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs active:scale-95 transition-all cursor-pointer"
            >
              {showSecrets ? <EyeOff size={13} /> : <Eye size={13} />}
              <span>{showSecrets ? 'Hide Secrets' : 'Show Secrets'}</span>
            </button>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {[
              { key: 'DATABASE_URL', val: 'postgresql://oil_admin:••••••••••••@127.0.0.1:5432/hsse_db' },
              { key: 'MODEL_STORAGE_PATH', val: '/var/models/quantized_v4/' },
              { key: 'OFFLINE_SYNC_TOKEN', val: 'oil_tok_sec_99482710482910481' },
              { key: 'LOCAL_ENCRYPTION_KEY', val: 'aes-256-gcm-master-key-prod-01' },
            ].map((item, idx) => (
              <div 
                key={idx} 
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200/60 hover:border-slate-300 hover:bg-slate-100/50 transition-all gap-2"
              >
                <span className="font-bold text-slate-700">{item.key}</span>
                <span className="text-slate-600 bg-white px-2.5 py-1 rounded border border-slate-200/80 font-mono shadow-2xs">
                  {showSecrets ? item.val.replace(/••••••••••••/, 'p@ssword_sec_2026') : item.val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">System Audit Trail</h2>
            <span className="text-xs font-mono text-slate-400">Showing last 24 hours</span>
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {logs.map((log) => (
              <div 
                key={log.id} 
                className="p-3.5 hover:bg-slate-50/90 hover:translate-x-0.5 transition-all duration-150 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${log.level === 'warning' ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900">{log.type}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono border border-slate-200/60">{log.id}</span>
                    </div>
                    <p className="text-slate-600 mt-0.5">{log.detail}</p>
                  </div>
                </div>
                <div className="text-right font-mono text-[11px] text-slate-400">
                  <div className="text-slate-600 font-medium">{log.user}</div>
                  <div>{log.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}