import React, { useState } from 'react';
import {
  ShieldCheck,
  Mail,
  Phone,
  Building2,
  Lock,
  Award,
  CheckCircle2,
  FileCheck,
  AlertTriangle,
  Shield,
  Edit3,
  ExternalLink,
  Download,
  Camera,
  X,
  UserCheck,
  HardHat,
  Save,
  Bell,
  KeyRound,
  Activity
} from 'lucide-react';

export default function HseAdminProfileView() {
  const [toastMessage, setToastMessage] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(true);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Profile Image State
  const [profilePhoto, setProfilePhoto] = useState(null);

  // Dynamic HSE Engineer Profile State
  const [profile, setProfile] = useState({
    name: 'Abhishek Jaiswal',
    title: 'Lead HSE Engineer',
    role: 'Senior Field Safety & Risk Assessment Engineer',
    employeeId: 'OIL-ENG-2026-104',
    department: 'Health, Safety & Environmental Engineering',
    organization: 'Oil India Limited (OIL)',
    location: 'Duliajan Operational Hub, Assam',
    email: 'abhi.engineer@oil.gov.in',
    phone: '+91 XXXYY XY210',
    clearanceLevel: 'Level 4 (Field Safety Override & SIF Auditor)',
    activeDutyStatus: 'On Duty / Senior Risk Lead',
    certifications: [
      { name: 'NEBOSH International Diploma in Occupational Health & Safety', validUntil: 'Dec 2028' },
      { name: 'ISO 45001:2018 Lead Auditor (OH&S Management)', validUntil: 'Aug 2027' },
      { name: 'Certified Safety Professional (CSP) - System Safety', validUntil: 'Nov 2029' },
      { name: 'Hazard Identification & Quantitative Risk Analysis (QRA)', validUntil: 'Permanent' },
    ]
  });

  // Temporary Form State for Editing Profile
  const [editFormData, setEditFormData] = useState({ ...profile });

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3000);
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setProfilePhoto(imageUrl);
      showToast('Profile photo updated successfully!');
    }
  };

  const handleSaveProfile = (e) => {
    e.preventDefault();
    setProfile({ ...editFormData });
    setIsEditModalOpen(false);
    showToast('HSE Engineer profile details updated!');
  };

  return (
    <div className="p-6 md:p-8 space-y-6 bg-slate-900/5 min-h-screen text-slate-800 relative font-sans antialiased">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 bg-slate-900 text-slate-100 px-4 py-3 rounded-xl shadow-2xl border border-slate-700/80 text-xs font-medium animate-in fade-in slide-in-from-bottom-5 duration-300 backdrop-blur-md">
          <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Breadcrumb */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
          <span className="hover:text-slate-800 transition-colors cursor-pointer">OIL HSSE</span>
          <span className="text-slate-300">/</span>
          <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/60">
            HSE Engineer Profile
          </span>
        </div>
        <button
          onClick={() => showToast('HSE Engineer credentials exported as PDF.')}
          className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200/90 text-slate-700 font-semibold text-xs hover:bg-slate-50 hover:border-emerald-300 hover:text-emerald-700 hover:shadow-md active:scale-95 transition-all duration-200 cursor-pointer"
        >
          <Download size={14} className="text-slate-400 group-hover:text-emerald-600 transition-colors" />
          <span>Export Credentials</span>
        </button>
      </div>

      {/* Profile Hero Card */}
      <div className="relative overflow-hidden rounded-3xl bg-slate-950 p-6 md:p-8 text-white shadow-xl border border-slate-800/80 group">
        {/* Glow Spheres */}
        <div className="absolute -top-20 -right-20 w-80 h-80 bg-teal-500/15 rounded-full blur-3xl pointer-events-none group-hover:bg-teal-500/25 transition-all duration-700" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none group-hover:bg-emerald-500/25 transition-all duration-700" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
            {/* Avatar / Profile Photo */}
            <div className="relative group/photo shrink-0">
              <div className="w-24 h-24 rounded-2xl bg-slate-900 border-2 border-emerald-500/40 group-hover/photo:border-emerald-400 flex items-center justify-center text-2xl font-black text-white shadow-2xl overflow-hidden transition-all duration-300">
                {profilePhoto ? (
                  <img src={profilePhoto} alt={profile.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="flex flex-col items-center justify-center text-teal-300">
                    <HardHat size={36} className="mb-0.5 text-emerald-400 group-hover/photo:scale-110 transition-transform duration-300" />
                    <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Engineer</span>
                  </div>
                )}
              </div>

              {/* Upload Overlay Button */}
              <label 
                htmlFor="photo-upload" 
                className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs rounded-2xl opacity-0 group-hover/photo:opacity-100 flex flex-col items-center justify-center text-white cursor-pointer transition-all duration-300 text-[10px] font-bold gap-1"
              >
                <Camera size={18} className="text-emerald-400 animate-bounce" />
                <span>Upload</span>
              </label>
              <input 
                type="file" 
                id="photo-upload" 
                accept="image/*" 
                onChange={handlePhotoUpload} 
                className="hidden" 
              />

              {/* Live Duty Status Indicator */}
              <span className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-500 border-2 border-slate-950 rounded-full flex items-center justify-center shadow-lg" title="Active Duty Status">
                <span className="w-2 h-2 bg-white rounded-full animate-ping" />
              </span>
            </div>

            <div className="space-y-1.5">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[10px] font-bold uppercase tracking-wider">
                <ShieldCheck size={13} className="text-emerald-400" />
                <span>{profile.clearanceLevel}</span>
              </div>
              
              <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex flex-wrap items-center gap-2.5">
                <span>{profile.name}</span>
                <span className="text-xs px-2.5 py-1 rounded-md bg-slate-800/90 text-teal-300 border border-slate-700/80 font-mono font-medium shadow-xs">
                  {profile.title}
                </span>
              </h1>
              
              <p className="text-xs text-slate-300 font-medium">{profile.role}</p>
              <p className="text-[11px] text-slate-400 font-mono flex items-center gap-2">
                <span>{profile.employeeId}</span>
                <span>•</span>
                <span>{profile.location}</span>
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col items-start md:items-end justify-between gap-3 shrink-0 pt-4 md:pt-0 border-t md:border-t-0 border-slate-800">
            <button
              onClick={() => {
                setEditFormData({ ...profile });
                setIsEditModalOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 active:scale-95 transition-all duration-200 cursor-pointer"
            >
              <Edit3 size={14} />
              <span>Edit Profile</span>
            </button>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300 font-mono">
              <Activity size={13} className="text-emerald-400 animate-pulse" />
              <span>Status: <strong className="text-emerald-400 font-semibold">{profile.activeDutyStatus}</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: HSE Engineering & Administrative Details */}
        <div className="space-y-6 lg:col-span-2">
          
          {/* Engineering Credentials & Operational Scope */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow duration-300 p-6 space-y-5">
            <h2 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
              <Building2 size={17} className="text-emerald-600" />
              <span>HSE Engineering & Operational Details</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-slate-50/70 hover:bg-slate-50 rounded-xl border border-slate-100 hover:border-emerald-200 hover:-translate-y-0.5 transition-all duration-200">
                <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider block mb-1">Engineering Division</span>
                <span className="font-semibold text-slate-800">{profile.department}</span>
              </div>

              <div className="p-4 bg-slate-50/70 hover:bg-slate-50 rounded-xl border border-slate-100 hover:border-emerald-200 hover:-translate-y-0.5 transition-all duration-200">
                <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider block mb-1">Organization</span>
                <span className="font-semibold text-slate-800">{profile.organization}</span>
              </div>

              <div className="p-4 bg-slate-50/70 hover:bg-slate-50 rounded-xl border border-slate-100 hover:border-emerald-200 hover:-translate-y-0.5 transition-all duration-200">
                <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider block mb-1">Official Work Email</span>
                <div className="flex items-center gap-2 font-mono text-slate-800 font-semibold">
                  <Mail size={14} className="text-emerald-600 shrink-0" />
                  <span className="truncate">{profile.email}</span>
                </div>
              </div>

              <div className="p-4 bg-slate-50/70 hover:bg-slate-50 rounded-xl border border-slate-100 hover:border-emerald-200 hover:-translate-y-0.5 transition-all duration-200">
                <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider block mb-1">Emergency Dispatch Hotline</span>
                <div className="flex items-center gap-2 font-mono text-slate-800 font-semibold">
                  <Phone size={14} className="text-emerald-600 shrink-0" />
                  <span>{profile.phone}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Technical Safety Certifications */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow duration-300 p-6 space-y-5">
            <h2 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
              <Award size={17} className="text-teal-600" />
              <span>HSE Engineering Certifications & Field Credentials</span>
            </h2>

            <div className="space-y-3">
              {profile.certifications.map((cert, idx) => (
                <div
                  key={idx}
                  className="group/cert flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-slate-50/60 hover:bg-emerald-50/30 rounded-xl border border-slate-100 hover:border-emerald-300/80 hover:-translate-y-0.5 transition-all duration-200 gap-3"
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-teal-50 group-hover/cert:bg-emerald-100 text-teal-700 group-hover/cert:text-emerald-800 border border-teal-200/60 group-hover/cert:border-emerald-300 flex items-center justify-center shrink-0 transition-colors">
                      <FileCheck size={18} />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 text-xs group-hover/cert:text-emerald-950 transition-colors">
                        {cert.name}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        Validity: <span className="text-slate-600">{cert.validUntil}</span>
                      </div>
                    </div>
                  </div>
                  <span className="self-start sm:self-center px-2.5 py-1 rounded-md bg-emerald-100/80 text-emerald-800 text-[10px] font-bold border border-emerald-300/60 shrink-0">
                    Active & Audited
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column: Privileges & Safety Dispatch Actions */}
        <div className="space-y-6">
          
          {/* Security Privileges */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow duration-300 p-6 space-y-5">
            <h2 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
              <Lock size={17} className="text-slate-700" />
              <span>Engineer Access & Controls</span>
            </h2>

            <div className="space-y-3 text-xs">
              {/* Toggle 1 */}
              <div className="flex items-center justify-between p-3.5 bg-slate-50/80 hover:bg-slate-50 rounded-xl border border-slate-100 transition-colors">
                <div className="flex items-center gap-3">
                  <KeyRound size={16} className="text-slate-500" />
                  <div>
                    <div className="font-semibold text-slate-800">Two-Factor Auth (2FA)</div>
                    <div className="text-[10px] text-slate-400">Enforced for Safety Override</div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setTwoFactorEnabled(!twoFactorEnabled);
                    showToast(`2FA ${!twoFactorEnabled ? 'Enabled' : 'Disabled'}`);
                  }}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-slate-900/20 ${
                    twoFactorEnabled ? 'bg-emerald-600' : 'bg-slate-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition duration-300 ease-in-out mt-1 ml-1 ${
                      twoFactorEnabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Toggle 2 */}
              <div className="flex items-center justify-between p-3.5 bg-slate-50/80 hover:bg-slate-50 rounded-xl border border-slate-100 transition-colors">
                <div className="flex items-center gap-3">
                  <Bell size={16} className="text-slate-500" />
                  <div>
                    <div className="font-semibold text-slate-800">Field Emergency Alerts</div>
                    <div className="text-[10px] text-slate-400">Push SMS & Direct SIF Broadcast</div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setNotificationsEnabled(!notificationsEnabled);
                    showToast(`Alerts ${!notificationsEnabled ? 'Enabled' : 'Disabled'}`);
                  }}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-slate-900/20 ${
                    notificationsEnabled ? 'bg-emerald-600' : 'bg-slate-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition duration-300 ease-in-out mt-1 ml-1 ${
                      notificationsEnabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <button
                onClick={() => showToast('Password reset link dispatched to your work email.')}
                className="w-full py-2.5 bg-slate-100 hover:bg-slate-200/90 text-slate-700 font-semibold rounded-xl text-xs hover:shadow-xs active:scale-98 transition-all duration-200 cursor-pointer text-center block"
              >
                Change Admin Password
              </button>
            </div>
          </div>

          {/* Quick HSE Action Panel */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow duration-300 p-6 space-y-4">
            <h2 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
              <Shield size={17} className="text-rose-600" />
              <span>Incident Command Dispatch</span>
            </h2>

            <button
              onClick={() => showToast('Initiated SIF High-Priority Safety Broadcast!')}
              className="w-full flex items-center justify-between p-4 rounded-xl bg-rose-50 hover:bg-rose-100/80 border border-rose-200/80 hover:border-rose-300 text-rose-900 font-bold text-xs transition-all duration-200 cursor-pointer group shadow-xs active:scale-98"
            >
              <div className="flex items-center gap-2.5">
                <AlertTriangle size={17} className="text-rose-600 group-hover:scale-110 transition-transform duration-200" />
                <span>Broadcast SIF Field Alert</span>
              </div>
              <ExternalLink size={14} className="text-rose-500 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>

        </div>
      </div>

      {/* EDIT PROFILE MODAL */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-100 overflow-hidden animate-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-slate-950 text-white border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <UserCheck size={18} className="text-emerald-400" />
                <h3 className="font-bold text-sm">Edit HSE Engineer Profile</h3>
              </div>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSaveProfile} className="p-6 space-y-4 text-xs font-medium text-slate-700">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={editFormData.name}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Engineering Title</label>
                  <input
                    type="text"
                    required
                    value={editFormData.title}
                    onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Role Description</label>
                <input
                  type="text"
                  required
                  value={editFormData.role}
                  onChange={(e) => setEditFormData({ ...editFormData, role: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Work Email</label>
                  <input
                    type="email"
                    required
                    value={editFormData.email}
                    onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white font-mono transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Emergency Hotline</label>
                  <input
                    type="text"
                    required
                    value={editFormData.phone}
                    onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white font-mono transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Department</label>
                  <input
                    type="text"
                    required
                    value={editFormData.department}
                    onChange={(e) => setEditFormData({ ...editFormData, department: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Location / Hub</label>
                  <input
                    type="text"
                    required
                    value={editFormData.location}
                    onChange={(e) => setEditFormData({ ...editFormData, location: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">Duty Status</label>
                <input
                  type="text"
                  required
                  value={editFormData.activeDutyStatus}
                  onChange={(e) => setEditFormData({ ...editFormData, activeDutyStatus: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 focus:bg-white transition-all"
                />
              </div>

              {/* Form Actions */}
              <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold cursor-pointer transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold cursor-pointer transition-all shadow-md active:scale-95"
                >
                  <Save size={14} />
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}