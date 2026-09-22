import React, { useState } from 'react';
import { Flag, Zap } from 'lucide-react';

export default function TriageQueue({
  reports,
  selectedReportId,
  setSelectedReportId,
  handleConfirmPsif,
  handleMarkNonSif,
  handleAgreeAllNonEvents,
  renderVerdictBadge
}) {
  const [activeTab, setActiveTab] = useState('all');
  const [selectedRowIds, setSelectedRowIds] = useState([selectedReportId]);

  const selectedReport = reports.find((r) => r.id === selectedReportId) || reports[0];

  const handleRowSelect = (id) => {
    setSelectedReportId(id);
    if (!selectedRowIds.includes(id)) {
      setSelectedRowIds([...selectedRowIds, id]);
    }
  };

  const toggleRowCheckbox = (id, e) => {
    e.stopPropagation();
    if (selectedRowIds.includes(id)) {
      setSelectedRowIds(selectedRowIds.filter((item) => item !== id));
    } else {
      setSelectedRowIds([...selectedRowIds, id]);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <div className="lg:col-span-7 space-y-3">
        <div className="flex flex-wrap items-center justify-between border-b border-gray-200 pb-2">
          <div className="flex items-center gap-4 text-xs font-semibold">
            {['all', 'uncertain', 'disagreements', 'language'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-2 capitalize transition cursor-pointer ${
                  activeTab === tab
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-black'
                }`}
              >
                {tab === 'all'
                  ? 'All 186'
                  : tab === 'uncertain'
                  ? 'Uncertain lane 24'
                  : tab === 'disagreements'
                  ? 'Disagreements 17'
                  : 'Language-weak 9'}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-400">{selectedRowIds.length} selected</span>
            <button
              onClick={handleAgreeAllNonEvents}
              className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 shadow-xs cursor-pointer"
            >
              Agree all Non-Event (14)
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-xs">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-gray-200 bg-gray-50/50 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="p-3 w-8">
                  <input
                    type="checkbox"
                    checked={selectedRowIds.length === reports.length}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedRowIds(reports.map((r) => r.id));
                      else setSelectedRowIds([]);
                    }}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="p-3">Verdict</th>
                <th className="p-3">Report ID</th>
                <th className="p-3">Site</th>
                <th className="p-3">Date</th>
                <th className="p-3">Energy</th>
                <th className="p-3">Rule</th>
                <th className="p-3">Barrier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => handleRowSelect(item.id)}
                  className={`cursor-pointer transition hover:bg-slate-50 ${
                    selectedReportId === item.id ? 'bg-sky-50/60' : ''
                  }`}
                >
                  <td className="p-3">
                    <input
                      type="checkbox"
                      checked={selectedRowIds.includes(item.id)}
                      onClick={(e) => toggleRowCheckbox(item.id, e)}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="p-3">{renderVerdictBadge(item.verdict)}</td>
                  <td className="p-3 font-mono font-medium text-gray-800">{item.id}</td>
                  <td className="p-3 text-gray-700">{item.site}</td>
                  <td className="p-3 text-gray-500 font-mono">{item.date}</td>
                  <td className="p-3 font-mono text-gray-600">{item.energy}</td>
                  <td className="p-3 font-bold text-gray-700">{item.rule}</td>
                  <td className="p-3">
                    <span
                      className={`text-[11px] font-medium ${
                        item.barrier === 'absent'
                          ? 'text-red-600'
                          : item.barrier === 'ineffective'
                          ? 'text-amber-600'
                          : 'text-gray-500'
                      }`}
                    >
                      {item.barrier}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
 
      <div className="lg:col-span-5">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-xs sticky top-4 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold font-mono text-gray-900">
                {selectedReport.id}
              </span>
              {renderVerdictBadge(selectedReport.verdict)}
            </div>
            <button
              onClick={() => alert(`Report ${selectedReport.id} flagged!`)}
              className="flex items-center gap-1 rounded-md bg-[#b91c1c] px-3 py-1 text-xs font-semibold text-white shadow-xs hover:bg-[#991b1b] cursor-pointer"
            >
              <Flag size={12} /> FLAG
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Site</span>
              <p className="font-semibold text-gray-900 mt-0.5">{selectedReport.site}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Date · Time</span>
              <p className="font-semibold text-gray-900 mt-0.5 font-mono text-[11px]">{selectedReport.fullDate}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Source Type</span>
              <p className="font-semibold text-gray-900 mt-0.5">{selectedReport.sourceType}</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs border-t border-gray-100 pt-3">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Reporter Role</span>
              <p className="font-semibold text-gray-900 mt-0.5">{selectedReport.role}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Activity</span>
              <p className="font-semibold text-gray-900 mt-0.5">{selectedReport.activity}</p>
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Language</span>
              <p className="font-semibold text-gray-900 mt-0.5">{selectedReport.language}</p>
            </div>
          </div>

          <div className="rounded-lg bg-gray-50 border border-gray-100 p-3">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">
              Report Text
            </span>
            <p className="text-xs text-gray-800 leading-relaxed font-sans">{selectedReport.text}</p>
          </div>

          <div className="text-xs text-gray-500 space-y-1">
            <div className="flex items-center gap-1.5">
              <Zap size={13} className="text-teal-600" />
              <span>Classified 2.1 s ago · rule engine v4.2</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-600">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              <span>
                Status: {selectedReport.reviewStatus} · in queue{' '}
                <strong className="text-gray-800">{selectedReport.inQueue}</strong>
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              onClick={() => handleConfirmPsif(selectedReport.id)}
              className="rounded-lg bg-[#b91c1c] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#991b1b] cursor-pointer"
            >
              Confirm P-SIF
            </button>
            <button
              onClick={() => handleMarkNonSif(selectedReport.id)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 shadow-xs cursor-pointer"
            >
              Mark Non-SIF
            </button>
            <button
              onClick={() => alert(`Clarification requested from ${selectedReport.role}`)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 shadow-xs cursor-pointer"
            >
              Request Info
            </button>
            <button
              onClick={() => {
                const note = prompt('Add HSE review note:');
                if (note) alert('Note saved!');
              }}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 shadow-xs cursor-pointer"
            >
              Add Note
            </button>
          </div>

          <div className="border-t border-gray-100 pt-3">
            <div className="flex justify-between items-center text-xs">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                Detected Energy Level
              </span>
              <span className="font-mono font-bold text-gray-900">{selectedReport.energy}</span>
            </div>
            <div className="mt-1.5 h-2 w-full rounded-full bg-gray-100 overflow-hidden">
              <div
                style={{
                  width: `${Math.min(100, Math.max(5, (selectedReport.energyValue / 9000) * 100))}%`
                }}
                className="h-full rounded-full bg-linear-to-r from-amber-500 to-red-600 transition-all duration-300"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}