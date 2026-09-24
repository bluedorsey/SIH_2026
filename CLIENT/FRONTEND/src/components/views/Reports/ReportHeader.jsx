import React from 'react';
import { Sparkles } from 'lucide-react';

export default function ReportHeader() {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-linear-to-r from-[#003c36] via-[#00534b] to-[#00665b] p-5 sm:p-6 text-white shadow-sm">
 
      <div className="absolute -right-16 -top-20 w-64 h-64 rounded-full bg-white/5 pointer-events-none" />

      <div className="relative z-10">
 
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-emerald-100 text-[11px] font-semibold">

          <Sparkles size={12} />

          Automated Intelligence

        </div>
 
        <h1 className="mt-2 text-xl sm:text-2xl font-extrabold tracking-tight">
          Reports & Executive Intelligence
        </h1>
 
        <p className="mt-1 max-w-2xl text-xs sm:text-sm text-emerald-100/80 leading-relaxed">
          Explore safety compliance summaries, SIF precursor metrics,
          and site risk logs.
        </p>

      </div>

    </div>
  );
}