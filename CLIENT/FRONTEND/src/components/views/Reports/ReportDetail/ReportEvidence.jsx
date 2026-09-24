import React from 'react';
import { HelpCircle, FileText, Layers, Zap } from 'lucide-react';

export default function ReportEvidence({ report, spans, fullOutput }) {
  const rawText = report?.raw_text || '';
  const eei = fullOutput?.eei_facts || {};
  const safetyKnowledge = fullOutput?.safety_knowledge || {};
  const energy = fullOutput?.energy || {};

  const renderHighlightedText = () => {
    if (!spans?.length) {
      return rawText;
    }

    const sortedSpans = [...spans]
      .filter(
        (span) => span.char_start !== undefined && span.char_end !== undefined
      )
      .sort((a, b) => a.char_start - b.char_start);

    if (!sortedSpans.length) {
      return rawText;
    }

    const result = [];
    let currentIndex = 0;

    sortedSpans.forEach((span, index) => {
      const start = span.char_start;
      const end = span.char_end;

      if (start > currentIndex) {
        result.push(
          <span key={`normal-${index}`}>
            {rawText.substring(currentIndex, start)}
          </span>
        );
      }

      let highlight = 'bg-gray-200 text-gray-800';

      if (span.role === 'energy_cue') {
        highlight = 'bg-orange-200 text-orange-900';
      } else if (span.role === 'release_cue') {
        highlight = 'bg-pink-200 text-pink-900';
      } else if (span.role === 'exposure_cue') {
        highlight = 'bg-purple-200 text-purple-900';
      } else if (span.role === 'control_present') {
        highlight = 'bg-green-200 text-green-900';
      } else if (span.role === 'control_absent') {
        highlight = 'bg-red-200 text-red-900';
      } else if (span.role === 'control_ineffective') {
        highlight = 'bg-yellow-200 text-yellow-900';
      }

      result.push(
        <mark
          key={`highlight-${index}`}
          className={`
            px-1
            rounded
            font-semibold
            ${highlight}
          `}
          title={span.role}
        >
          {rawText.substring(start, end)}
        </mark>
      );

      currentIndex = end;
    });

    if (currentIndex < rawText.length) {
      result.push(
        <span key="remaining">
          {rawText.substring(currentIndex)}
        </span>
      );
    }

    return result;
  };

  const eeiQuestions = [
    { label: 'High Energy Present', key: 'high_energy_present' },
    { label: 'Energy Released', key: 'energy_released' },
    { label: 'Serious Injury', key: 'serious_injury' },
    { label: 'Direct Control Present', key: 'direct_control_present' },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-stretch">
        <div className="xl:col-span-8 min-w-0 bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100 shrink-0">
            <FileText size={16} className="text-teal-700" />
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
              Evidence in Text
            </h3>
          </div>

          <div className="mt-4 min-h-[250px] flex-1 bg-slate-50 border border-slate-100 rounded-lg p-4 text-sm leading-relaxed whitespace-pre-wrap break-words overflow-hidden">
            {renderHighlightedText()}
          </div>

          <div className="mt-4 shrink-0">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
              Detected Spans
            </h4>

            <div className="flex flex-wrap gap-2">
              {spans?.length > 0 ? (
                spans.map((span, index) => {
                  const text =
                    span.text_span ||
                    rawText.substring(span.char_start, span.char_end);

                  return (
                    <span
                      key={index}
                      className="max-w-full px-2 py-1 rounded-md bg-purple-50 border border-purple-200 text-[10px] font-semibold text-purple-700 break-words"
                    >
                      {String(span.role || 'span').replace(/_/g, ' ')}
                      : "{text}"
                    </span>
                  );
                })
              ) : (
                <span className="text-xs text-slate-400 italic">
                  No specific spans detected.
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="xl:col-span-4 min-w-0 bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100 shrink-0">
            <HelpCircle size={16} className="text-teal-700" />
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
              The Four Questions (EEI)
            </h3>
          </div>

          <div className="mt-4 space-y-3">
            {eeiQuestions.map((question) => {
              const fact = eei?.[question.key];

              if (!fact) {
                return null;
              }

              return (
                <div
                  key={question.key}
                  className="bg-slate-50 rounded-lg border border-slate-100 p-3 min-w-0"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold text-slate-700 leading-tight">
                      {question.label}
                    </span>

                    <span
                      className={`
                        shrink-0
                        px-2
                        py-0.5
                        rounded
                        text-[10px]
                        font-bold
                        ${
                          fact.value
                            ? 'bg-red-100 text-red-700'
                            : 'bg-green-100 text-green-700'
                        }
                      `}
                    >
                      {fact.value ? 'TRUE' : 'FALSE'}
                    </span>
                  </div>

                  {fact.span && (
                    <p className="mt-2 text-[10px] text-slate-500 italic wrap-break-word">
                      "{fact.span}"
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm min-w-0">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Layers size={15} className="text-teal-700" />
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Safety Knowledge
            </h3>
          </div>

          <div className="mt-3 space-y-3 text-xs">
            <InfoRow
              label="Hazard"
              value={String(safetyKnowledge?.hazard || 'Unknown').replace(/_/g, ' ')}
            />
            <InfoRow
              label="Required Barrier"
              value={String(safetyKnowledge?.barrier || 'Unknown').replace(/_/g, ' ')}
            />
            <InfoRow
              label="LSR / Rules"
              value={safetyKnowledge?.lsr?.join(', ') || 'None'}
            />
            <InfoRow
              label="Potential Consequence"
              value={String(safetyKnowledge?.potential_consequence || 'Unknown').replace(/_/g, ' ')}
            />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm min-w-0">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Zap size={15} className="text-teal-700" />
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Energy
            </h3>
          </div>

          <div className="mt-3 space-y-3 text-xs">
            <InfoRow
              label="Type"
              value={String(energy?.type || 'Unknown').replace(/_/g, ' ')}
            />
            <InfoRow
              label="Estimate (Joules)"
              value={
                energy?.estimate_j !== undefined
                  ? Number(energy.estimate_j).toLocaleString()
                  : '—'
              }
            />
            <InfoRow
              label="SIF Threshold (Joules)"
              value={
                energy?.threshold_j !== undefined
                  ? Number(energy.threshold_j).toLocaleString()
                  : '—'
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div>
      <p className="text-slate-400 font-semibold">{label}</p>
      <p className="font-bold text-slate-800 break-words">{value}</p>
    </div>
  );
}