import React from 'react';

import {
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  Info,
  Clock,
} from 'lucide-react';

export default function ReportOverview({
  report,
  verdict,
  fullOutput,
}) {
  const verdictValue =
    verdict?.verdict || 'UNKNOWN';

  const verdictUpper =
    String(verdictValue).toUpperCase();

  const verdictDetail =
    fullOutput?.verdict_detail || {};

  const getVerdictStyle = () => {
    if (verdictUpper === 'EXPOSURE') {
      return {
        bg: 'bg-gradient-to-r from-yellow-600 to-amber-500',
        icon: <AlertCircle size={25} />,
      };
    }

    if (
      verdictUpper === 'H_SIF' ||
      verdictUpper === 'P_SIF'
    ) {
      return {
        bg: 'bg-gradient-to-r from-red-700 to-red-600',
        icon: <ShieldAlert size={25} />,
      };
    }

    if (
      verdictUpper === 'NON_EVENT' ||
      verdictUpper === 'SUCCESS'
    ) {
      return {
        bg: 'bg-gradient-to-r from-emerald-700 to-green-600',
        icon: <CheckCircle size={25} />,
      };
    }

    if (verdictUpper === 'LOW_ENERGY') {
      return {
        bg: 'bg-gradient-to-r from-teal-700 to-teal-600',
        icon: <Info size={25} />,
      };
    }

    if (verdictUpper === 'CAPACITY') {
      return {
        bg: 'bg-gradient-to-r from-orange-600 to-amber-500',
        icon: <AlertTriangle size={25} />,
      };
    }

    return {
      bg: 'bg-slate-600',
      icon: <HelpCircle size={25} />,
    };
  };

  const verdictStyle = getVerdictStyle();

  return (
    <>
      <div
        className={`
          rounded-xl
          p-4
          sm:p-5
          text-white
          shadow-sm
          ${verdictStyle.bg}
        `}
      >
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-center">

          <div className="flex items-center gap-3 min-w-0">

            <div className="p-3 rounded-full bg-white/15 shrink-0">
              {verdictStyle.icon}
            </div>

            <div className="min-w-0">

              <p className="text-[11px] font-bold uppercase opacity-80">
                Verdict
              </p>

              <h2 className="text-2xl sm:text-3xl font-black wrap-break-word">
                {verdictValue}
              </h2>

              <p className="text-xs opacity-80 capitalize">
                {String(verdictValue)
                  .replace(/_/g, ' ')
                  .toLowerCase()}{' '}
                event
              </p>

            </div>

          </div>

          <div className="md:border-x border-white/20 px-4 text-left md:text-center">

            <p className="text-[11px] font-bold uppercase opacity-80">
              Confidence
            </p>

            <p className="text-2xl sm:text-3xl font-black">
              {verdict?.confidence !== undefined
                ? `${(
                    Number(verdict.confidence) * 100
                  ).toFixed(0)}%`
                : 'N/A'}
            </p>

            <p className="text-[10px] opacity-80">
              Route:{' '}
              {verdictDetail?.route || 'Unknown'}
            </p>

          </div>

          <div className="md:text-right min-w-0">

            <p className="text-[10px] uppercase font-bold opacity-70">
              Report ID
            </p>

            <p className="font-mono text-xs break-all">
              {report?.id ||
                report?.metadata?.report_id ||
                'Unknown'}
            </p>

            <p className="text-[10px] opacity-70 mt-1 flex md:justify-end items-center gap-1">

              <Clock size={10} />

              {report?.ingested_at
                ? new Date(
                    report.ingested_at
                  ).toLocaleString()
                : 'Unknown'}

            </p>

          </div>

        </div>
      </div>

      {verdictDetail?.decision_path && (
        <div className="rounded-lg bg-slate-800 text-slate-200 p-3 text-[11px] font-mono overflow-hidden">

          <div className="flex flex-col sm:flex-row gap-2">

            <span className="font-bold text-slate-400 shrink-0">
              DECISION PATH
            </span>

            <span className="hidden sm:block text-slate-500">
              |
            </span>

            <span className="whitespace-normal wrap-break-word leading-relaxed">
              {String(
                verdictDetail.decision_path
              ).replace(/->/g, '→')}
            </span>

          </div>

        </div>
      )}
    </>
  );
}