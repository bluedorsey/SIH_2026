import React, { useEffect, useState } from 'react';
import { FileText, Loader2, AlertCircle } from 'lucide-react';

import { getReports, getReportDetail } from '../../services/api';

import ReportHeader from './Reports/ReportHeader';
import ReportRegistry from './Reports/ReportRegistry';
import ReportDetail from './Reports/ReportDetail';

export default function ReportsView() {
  const [searchTerm, setSearchTerm] = useState('');

  const [reportsList, setReportsList] = useState([]);
  const [loadingList, setLoadingList] = useState(true);

  const [selectedReportId, setSelectedReportId] = useState(null);

  const [reportDetail, setReportDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState('');

  useEffect(() => {
    async function loadReports() {
      try {
        setLoadingList(true);

        const data = await getReports(1, 50);
        const reports = data?.data || [];

        setReportsList(reports);

        if (reports.length > 0) {
          setSelectedReportId(reports[0].report_id);
        }
      } catch (error) {
        console.error('Failed to load reports:', error);
      } finally {
        setLoadingList(false);
      }
    }

    loadReports();
  }, []);

  useEffect(() => {
    async function loadReportDetail() {
      if (!selectedReportId) {
        setReportDetail(null);
        return;
      }

      try {
        setLoadingDetail(true);
        setDetailError('');

        const detail = await getReportDetail(selectedReportId);

        setReportDetail(detail);
      } catch (error) {
        console.error('Failed to load report detail:', error);
        setDetailError('Failed to load report details.');
      } finally {
        setLoadingDetail(false);
      }
    }

    loadReportDetail();
  }, [selectedReportId]);

  const filteredReports = reportsList.filter((report) => {
    const term = searchTerm.toLowerCase().trim();

    if (!term) return true;

    return (
      String(report.report_id || '')
        .toLowerCase()
        .includes(term) ||
      String(report.site_code || '')
        .toLowerCase()
        .includes(term) ||
      String(report.verdict || '')
        .toLowerCase()
        .includes(term)
    );
  });

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 p-3 sm:p-4 lg:p-6 overflow-x-hidden">
      <ReportHeader />
      <div className="grid grid-cols-1 2xl:grid-cols-12 gap-5 lg:gap-6 mt-5">

        {/* REPORT REGISTRY */}
        <div className="min-w-0 2xl:col-span-7">
          <ReportRegistry
            reports={filteredReports}
            loading={loadingList}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            selectedReportId={selectedReportId}
            setSelectedReportId={setSelectedReportId}
          />
        </div>

        {/* REPORT DETAIL */}
        <div className="min-w-0 2xl:col-span-5">

          <div className="bg-white border border-slate-200 rounded-xl shadow-sm h-auto 2xl:h-[800px] overflow-y-auto overflow-x-hidden">

            {loadingDetail ? (

              <div className="min-h-[500px] flex flex-col items-center justify-center gap-3 text-slate-500">

                <Loader2
                  size={30}
                  className="animate-spin text-teal-600"
                />

                <p className="text-sm font-medium">
                  Loading report details...
                </p>

              </div>

            ) : detailError ? (

              <div className="min-h-[500px] flex flex-col items-center justify-center gap-3 text-red-500 px-6">

                <AlertCircle size={32} />

                <p className="text-sm font-medium text-center">
                  {detailError}
                </p>

              </div>

            ) : reportDetail ? (

              <ReportDetail data={reportDetail} />

            ) : (

              <div className="min-h-[500px] flex flex-col items-center justify-center gap-3 text-slate-400">

                <FileText
                  size={45}
                  className="opacity-30"
                />

                <p className="text-sm font-medium text-center">
                  Select a report to view its details
                </p>

              </div>

            )}

          </div>

        </div>

      </div>

    </div>
  );
}