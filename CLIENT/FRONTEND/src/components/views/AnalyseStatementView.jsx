import React, { useEffect, useState } from "react";
import {
  Zap,
  ShieldAlert,
  CheckCircle2,
  FileText,
  Loader2,
  ArrowRight,
  Info,
  Upload,
  FileSpreadsheet,
  FileCode,
  X,
  Database,
  Type,
  AlertCircle,
} from "lucide-react";

import { analyseReport, analyseBatch } from "../../services/api";

export default function AnalyseStatementView() {
  const [analysisMode, setAnalysisMode] = useState("file");

  const [statement, setStatement] = useState("");
  const [site, setSite] = useState("");
  const [activity, setActivity] = useState("");

  const [uploadedFile, setUploadedFile] = useState(null);
  const [parsedData, setParsedData] = useState([]);
  const [fileError, setFileError] = useState("");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [batchResults, setBatchResults] = useState(null);
  const [apiError, setApiError] = useState("");

  const examplePrompts = [
    {
      text: "Crane lifting 2 ton pipe over workers, sling was frayed and tag lines were missing.",
      site: "Duliajan Yard",
      activity: "Lifting Operations",
    },
    {
      text: "Monkey board se tool box neeche gira, barricading nahi tha aur derrick man bina harness ke tha.",
      site: "Rig #07 Digboi",
      activity: "Drilling / Derrick Work",
    },
    {
      text: "Hot work near wellhead without gas test certificate or fire watch present.",
      site: "Wellhead #14 Naharkatiya",
      activity: "Welding & Cutting",
    },
    {
      text: "AC ka remote kharab ho gaya canteen me, repair required.",
      site: "Central Canteen",
      activity: "Facility Management",
    },
  ];

  // ---------------------------------------------------------
  // CSV PARSER
  // ---------------------------------------------------------

  const parseCSV = (csvText) => {
    const lines = csvText
      .split(/\r\n|\n/)
      .filter((line) => line.trim() !== "");

    if (lines.length < 2) return [];

    const headers = lines[0]
      .split(",")
      .map((h) => h.trim().toLowerCase());

    const statementIndex = headers.findIndex(
      (h) =>
        h.includes("statement") ||
        h.includes("report") ||
        h.includes("observation") ||
        h.includes("description") ||
        h.includes("text")
    );

    const siteIndex = headers.findIndex(
      (h) =>
        h.includes("site") ||
        h.includes("location") ||
        h.includes("yard")
    );

    const activityIndex = headers.findIndex(
      (h) =>
        h.includes("activity") ||
        h.includes("operation") ||
        h.includes("work")
    );

    const parsed = [];

    for (let i = 1; i < lines.length; i++) {
      const values =
        lines[i].match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) ||
        lines[i].split(",");

      const cleanValues = values.map((value) =>
        value.replace(/^"|"$/g, "").trim()
      );

      const statementValue =
        statementIndex !== -1
          ? cleanValues[statementIndex]
          : cleanValues[0];

      const siteValue =
        siteIndex !== -1 ? cleanValues[siteIndex] : cleanValues[1] || "";

      const activityValue =
        activityIndex !== -1
          ? cleanValues[activityIndex]
          : cleanValues[2] || "";

      if (statementValue) {
        parsed.push({
          text: statementValue,
          site: siteValue,
          activity: activityValue,
        });
      }
    }

    return parsed;
  };

  // ---------------------------------------------------------
  // FILE UPLOAD
  // ---------------------------------------------------------

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setFileError("");
    setApiError("");
    setUploadedFile(file);
    setParsedData([]);
    setBatchResults(null);
    setResult(null);

    const reader = new FileReader();

    if (file.name.toLowerCase().endsWith(".json")) {
      reader.onload = (e) => {
        try {
          const json = JSON.parse(e.target.result);

          const formatted = Array.isArray(json)
            ? json
                .map((item) => ({
                  text:
                    item.statement ||
                    item.text ||
                    item.observation ||
                    item.report ||
                    "",
                  site: item.site || item.location || "",
                  activity: item.activity || item.operation || "",
                }))
                .filter((item) => item.text)
            : [];

          if (formatted.length === 0) {
            setFileError(
              'Invalid JSON format. Expected an array containing objects with a "statement" or "text" field.'
            );
          } else {
            setParsedData(formatted);
          }
        } catch {
          setFileError(
            "Failed to parse JSON file. Please check the file syntax."
          );
        }
      };

      reader.readAsText(file);
    } else if (file.name.toLowerCase().endsWith(".csv")) {
      reader.onload = (e) => {
        try {
          const data = parseCSV(e.target.result);

          if (data.length === 0) {
            setFileError("Could not extract valid records from CSV.");
          } else {
            setParsedData(data);
          }
        } catch {
          setFileError("Failed to parse CSV file.");
        }
      };

      reader.readAsText(file);
    } else {
      setFileError(
        "Unsupported file format. Please upload a .csv or .json file."
      );
      setUploadedFile(null);
    }
  };

  // ---------------------------------------------------------
  // SINGLE REPORT ANALYSIS
  // ---------------------------------------------------------

  const handleSingleAnalysis = async () => {
    if (!statement.trim() || loading) return;

    setLoading(true);
    setResult(null);
    setApiError("");

    try {
      const response = await analyseReport(statement.trim(), "", {
        site: site.trim(),
        activity: activity.trim(),
      });

      setResult(response);
    } catch (error) {
      console.error("OILENS analysis error:", error);

      setApiError(
        error?.message ||
          "Unable to connect to the OILENS analysis engine."
      );
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------
  // BATCH ANALYSIS
  // ---------------------------------------------------------

  const handleBatchAnalysis = async () => {
    if (parsedData.length === 0 || loading) return;

    setLoading(true);
    setBatchResults(null);
    setApiError("");

    try {
      /*
       * Each record keeps the same structure already used
       * by your frontend.
       *
       * If your FastAPI /batch endpoint expects a wrapper
       * object instead, we can adjust this after checking
       * api.py.
       */

      const payload = parsedData.map((item, index) => ({
        text: item.text,
        report_id: `OILENS-BATCH-${index + 1}`,
        meta: {
          site: item.site || "",
          activity: item.activity || "",
        },
      }));

      const response = await analyseBatch(payload);

      setBatchResults(response);
    } catch (error) {
      console.error("OILENS batch analysis error:", error);

      setApiError(
        error?.message ||
          "Unable to process the uploaded dataset."
      );
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------
  // MAIN ANALYSIS HANDLER
  // ---------------------------------------------------------

  const handleAnalyse = async () => {
    if (analysisMode === "text") {
      await handleSingleAnalysis();
    } else {
      await handleBatchAnalysis();
    }
  };

  // ---------------------------------------------------------
  // REMOVE FILE
  // ---------------------------------------------------------

  const removeFile = () => {
    setUploadedFile(null);
    setParsedData([]);
    setFileError("");
    setApiError("");
    setBatchResults(null);
  };

  // ---------------------------------------------------------
  // CTRL + ENTER
  // ---------------------------------------------------------

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key === "Enter"
      ) {
        event.preventDefault();
        handleAnalyse();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    statement,
    site,
    activity,
    parsedData,
    analysisMode,
    loading,
  ]);

  // ---------------------------------------------------------
  // HELPERS
  // ---------------------------------------------------------

  const getVerdict = (data) => {
    if (!data) return "UNKNOWN";

    const value = String(
      data.verdict ||
        data.risk ||
        data.sif_potential ||
        data.result ||
        ""
    ).toLowerCase();

    if (value.includes("high")) return "HIGH SIF POTENTIAL";
    if (value.includes("medium")) return "MEDIUM SIF POTENTIAL";
    if (value.includes("low")) return "LOW SIF POTENTIAL";

    return data.verdict || "ANALYSIS COMPLETE";
  };

  const getVerdictClass = (data) => {
    const verdict = getVerdict(data).toLowerCase();

    if (verdict.includes("high")) {
      return "bg-red-50 text-red-700 border-red-200";
    }

    if (verdict.includes("medium")) {
      return "bg-amber-50 text-amber-700 border-amber-200";
    }

    if (verdict.includes("low")) {
      return "bg-blue-50 text-blue-700 border-blue-200";
    }

    return "bg-slate-50 text-slate-700 border-slate-200";
  };

  const getVerdictIcon = (data) => {
    const verdict = getVerdict(data).toLowerCase();

    if (verdict.includes("high")) {
      return <ShieldAlert size={22} className="text-red-600" />;
    }

    return <CheckCircle2 size={22} className="text-slate-500" />;
  };

  const getField = (data, keys) => {
    if (!data) return "Not identified";

    for (const key of keys) {
      const value = data?.[key];

      if (
        value !== undefined &&
        value !== null &&
        value !== ""
      ) {
        if (typeof value === "object") {
          return JSON.stringify(value, null, 2);
        }

        return String(value);
      }
    }

    return "Not identified";
  };

  const isButtonDisabled =
    loading ||
    (analysisMode === "text" && !statement.trim()) ||
    (analysisMode === "file" && parsedData.length === 0);

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <main className="flex-1 p-3 sm:p-4 md:p-5 space-y-4">

      {/* HEADER */}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">

        <div className="lg:col-span-6 xl:col-span-7 flex flex-col justify-center bg-white p-5 md:p-6 rounded-2xl border border-gray-200/80 shadow-sm space-y-3">

          <div className="inline-flex w-fit items-center gap-2 rounded-full bg-teal-50 px-3.5 py-1.5 text-xs font-bold text-[#00695c] border border-teal-100">
            <Zap size={14} />
            <span>OILENS SIF Intelligence</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-black text-[#0e1d2c] tracking-tight leading-tight">
            Analyse Safety Report
          </h1>

          <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
            Submit an unsafe-act, unsafe-condition, or near-miss
            report. OILENS extracts the relevant safety context and
            evaluates SIF potential using the analysis engine.
          </p>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Info size={14} />
            <span>
              AI assessment is decision support. Final review remains
              with the Safety Officer.
            </span>
          </div>
        </div>

        <div className="lg:col-span-6 xl:col-span-5 bg-white p-3 rounded-2xl border border-gray-200/80 shadow-sm flex items-center justify-center">

          <div className="w-full h-full min-h-[260px] relative overflow-hidden rounded-xl bg-slate-50 border border-slate-100 p-2 flex items-center justify-center group">

            <img
              src="/analyse.jpg"
              alt="OILENS safety report analysis"
              className="w-full h-auto max-h-72 sm:max-h-80 md:max-h-96 object-contain rounded-lg transition-transform duration-300 group-hover:scale-[1.02]"
            />

          </div>
        </div>
      </div>

      {/* INPUT CARD */}

      <div className="rounded-2xl border border-gray-200/80 bg-white p-4 sm:p-5 shadow-sm space-y-4">

        {/* MODE SELECTOR */}

        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">

          <button
            type="button"
            onClick={() => {
              setAnalysisMode("file");
              setResult(null);
              setBatchResults(null);
              setApiError("");
            }}
            className={
              analysisMode === "file"
                ? "flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-[#004e47] text-white shadow-sm"
                : "flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-gray-100 text-gray-600 hover:bg-gray-200"
            }
          >
            <Upload size={14} />
            <span>Upload CSV / JSON</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setAnalysisMode("text");
              setBatchResults(null);
              setApiError("");
            }}
            className={
              analysisMode === "text"
                ? "flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-[#004e47] text-white shadow-sm"
                : "flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-gray-100 text-gray-600 hover:bg-gray-200"
            }
          >
            <Type size={14} />
            <span>Single Statement</span>
          </button>

        </div>

        {/* FILE MODE */}

        {analysisMode === "file" && (
          <div className="space-y-4">

            {!uploadedFile ? (
              <label className="flex flex-col items-center justify-center w-full h-44 border-2 border-dashed border-teal-200 rounded-2xl cursor-pointer bg-teal-50/30 hover:bg-teal-50/60 transition-colors">

                <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center px-4">

                  <div className="p-3 bg-teal-100 text-[#00695c] rounded-full mb-2">
                    <Upload size={22} />
                  </div>

                  <p className="mb-1 text-sm font-bold text-gray-800">
                    Click to upload or drag & drop
                  </p>

                  <p className="text-xs text-gray-500">
                    Supports{" "}
                    <span className="font-semibold text-gray-700">
                      .CSV
                    </span>{" "}
                    or{" "}
                    <span className="font-semibold text-gray-700">
                      .JSON
                    </span>
                  </p>

                </div>

                <input
                  type="file"
                  accept=".csv,.json"
                  className="hidden"
                  onChange={handleFileUpload}
                />

              </label>
            ) : (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 bg-teal-50/50 border border-teal-200 rounded-xl gap-3">

                <div className="flex items-center gap-3">

                  <div className="p-2.5 bg-teal-600 text-white rounded-lg">
                    {uploadedFile.name
                      .toLowerCase()
                      .endsWith(".csv") ? (
                      <FileSpreadsheet size={20} />
                    ) : (
                      <FileCode size={20} />
                    )}
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-gray-900">
                      {uploadedFile.name}
                    </h4>

                    <p className="text-xs text-gray-500">
                      {(uploadedFile.size / 1024).toFixed(1)} KB
                      {" • "}
                      {parsedData.length} records detected
                    </p>
                  </div>

                </div>

                <button
                  type="button"
                  onClick={removeFile}
                  className="flex items-center gap-1 text-xs font-semibold text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg border border-rose-200"
                >
                  <X size={14} />
                  Remove File
                </button>

              </div>
            )}

            {/* FILE ERROR */}

            {fileError && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-600 font-medium">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <span>{fileError}</span>
              </div>
            )}

            {/* API ERROR */}

            {apiError && (
              <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-700">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Analysis engine unavailable</p>
                  <p className="mt-0.5">
                    {apiError}
                  </p>
                </div>
              </div>
            )}

            {/* PREVIEW */}

            {parsedData.length > 0 && (
              <div className="space-y-2">

                <div className="flex items-center justify-between">

                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Database size={13} />
                    File Preview ({parsedData.length})
                  </span>

                </div>

                <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-xl text-xs">

                  <table className="w-full text-left border-collapse">

                    <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 font-bold text-gray-600">

                      <tr>
                        <th className="p-2.5">#</th>
                        <th className="p-2.5">
                          Statement / Observation
                        </th>
                        <th className="p-2.5">Site</th>
                        <th className="p-2.5">Activity</th>
                      </tr>

                    </thead>

                    <tbody className="divide-y divide-gray-100 bg-white">

                      {parsedData.slice(0, 5).map((row, index) => (
                        <tr
                          key={index}
                          className="hover:bg-gray-50"
                        >
                          <td className="p-2.5 font-bold text-gray-400">
                            {index + 1}
                          </td>

                          <td className="p-2.5 text-gray-800 font-medium truncate max-w-xs">
                            {row.text}
                          </td>

                          <td className="p-2.5 text-gray-600">
                            {row.site || "—"}
                          </td>

                          <td className="p-2.5 text-gray-600">
                            {row.activity || "—"}
                          </td>
                        </tr>
                      ))}

                    </tbody>

                  </table>

                </div>

                {parsedData.length > 5 && (
                  <p className="text-[11px] text-gray-400 italic">
                    Showing first 5 rows out of {parsedData.length}.
                  </p>
                )}

              </div>
            )}

          </div>
        )}

        {/* TEXT MODE */}

        {analysisMode === "text" && (
          <div className="space-y-3">

            <textarea
              rows={5}
              value={statement}
              onChange={(e) => {
                setStatement(e.target.value);
                setResult(null);
                setApiError("");
              }}
              placeholder="Example: Worker entered a confined space without gas testing. No standby person was present."
              className="w-full resize-none rounded-xl border border-gray-200 p-3.5 text-sm text-gray-800 placeholder-gray-400 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
            />

            <div className="flex flex-wrap items-center gap-2.5">

              <input
                type="text"
                placeholder="Site (optional)"
                value={site}
                onChange={(e) => setSite(e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-700 placeholder-gray-400 focus:border-teal-600 focus:outline-none sm:w-44"
              />

              <input
                type="text"
                placeholder="Activity (optional)"
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-700 placeholder-gray-400 focus:border-teal-600 focus:outline-none sm:w-52"
              />

            </div>

            <div className="flex flex-wrap items-center gap-1.5">

              <span className="text-xs text-gray-400">
                Try:
              </span>

              {examplePrompts.map((prompt, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    setStatement(prompt.text);
                    setSite(prompt.site);
                    setActivity(prompt.activity);
                    setResult(null);
                    setApiError("");
                  }}
                  className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-medium text-[#00695c] hover:bg-teal-100 transition-colors"
                >
                  {prompt.text.slice(0, 32)}...
                </button>
              ))}

            </div>

            {apiError && (
              <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-700">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />

                <div>
                  <p className="font-bold">
                    Could not analyse the report
                  </p>

                  <p className="mt-0.5">
                    {apiError}
                  </p>
                </div>
              </div>
            )}

          </div>
        )}

        {/* ACTION */}

        <div className="mt-4 flex justify-end">

          <button
            type="button"
            disabled={isButtonDisabled}
            onClick={handleAnalyse}
            className={
              isButtonDisabled
                ? "flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-semibold bg-gray-300 cursor-not-allowed text-gray-500"
                : "flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-semibold text-white bg-[#004e47] hover:bg-[#08423d] active:scale-[0.98] cursor-pointer"
            }
          >

            {loading ? (
              <>
                <Loader2
                  size={14}
                  className="animate-spin"
                />

                <span>
                  {analysisMode === "file"
                    ? "Analysing Dataset..."
                    : "Analysing Report..."}
                </span>
              </>
            ) : (
              <>
                <Zap size={14} />

                <span>
                  {analysisMode === "file"
                    ? `Analyse ${parsedData.length} Records`
                    : "Analyse Report"}
                </span>

                <kbd className="ml-1 rounded bg-white/20 px-1 py-0.5 text-[10px] font-normal tracking-wide text-white">
                  Ctrl+↵
                </kbd>
              </>
            )}

          </button>

        </div>

      </div>

      {/* --------------------------------------------------- */}
      {/* SINGLE RESULT */}
      {/* --------------------------------------------------- */}

      {result && analysisMode === "text" && (
        <div className="rounded-2xl border border-gray-200/80 bg-white p-5 shadow-sm space-y-5">

          {/* HEADER */}

          <div className="flex flex-wrap items-center justify-between border-b border-gray-100 pb-4 gap-3">

            <div className="flex items-center gap-2">

              {getVerdictIcon(result)}

              <div>
                <h2 className="text-base font-bold text-gray-900">
                  SIF Assessment
                </h2>

                <p className="text-xs text-gray-500">
                  Analysis returned by OILENS
                </p>
              </div>

            </div>

            <span
              className={`rounded-full border px-3 py-1 text-xs font-bold ${getVerdictClass(
                result
              )}`}
            >
              {getVerdict(result)}
            </span>

          </div>

          {/* CORE FINDINGS */}

          <div>

            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
              Key Findings
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">

              <FindingCard
                title="Hazard"
                value={getField(result, [
                  "hazard",
                  "detected_hazard",
                  "hazards",
                ])}
              />

              <FindingCard
                title="Activity"
                value={
                  activity ||
                  getField(result, [
                    "activity",
                    "detected_activity",
                  ])
                }
              />

              <FindingCard
                title="Exposure"
                value={getField(result, [
                  "exposure",
                  "detected_exposure",
                ])}
              />

              <FindingCard
                title="Missing / Failed Control"
                value={getField(result, [
                  "failed_control",
                  "missing_control",
                  "control_failure",
                  "failed_controls",
                ])}
              />

              <FindingCard
                title="Potential Consequence"
                value={getField(result, [
                  "potential_consequence",
                  "consequence",
                  "harm",
                ])}
              />

            </div>

          </div>

          {/* REASONING */}

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

            <div className="flex items-center gap-2 mb-3">
              <Zap size={15} className="text-teal-700" />

              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                Assessment Reasoning
              </h3>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">

              <ReasoningStep label="Hazard" />

              <ArrowRight size={13} className="text-slate-400" />

              <ReasoningStep label="Exposure" />

              <ArrowRight size={13} className="text-slate-400" />

              <ReasoningStep label="Control Failure" />

              <ArrowRight size={13} className="text-slate-400" />

              <ReasoningStep label="Potential Consequence" />

              <ArrowRight size={13} className="text-slate-400" />

              <span
                className={`px-3 py-1.5 rounded-lg border font-bold ${getVerdictClass(
                  result
                )}`}
              >
                {getVerdict(result)}
              </span>

            </div>

          </div>

          {/* EVIDENCE */}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            <div className="rounded-xl border border-gray-200 p-4">

              <div className="flex items-center gap-2 mb-3">

                <FileText size={15} className="text-teal-700" />

                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Evidence From Report
                </h3>

              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">

                <p className="text-sm text-slate-700 leading-relaxed">
                  {statement}
                </p>

              </div>

            </div>

            <div className="rounded-xl border border-gray-200 p-4">

              <div className="flex items-center gap-2 mb-3">

                <Info size={15} className="text-teal-700" />

                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Relevant Domain Knowledge
                </h3>

              </div>

              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                {getField(result, [
                  "safety_knowledge",
                  "domain_knowledge",
                  "knowledge",
                ])}
              </p>

            </div>

          </div>

          {/* RAW SUPPORTING INFORMATION */}

          <details className="rounded-xl border border-gray-200">

            <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-slate-600 hover:bg-slate-50">
              View technical analysis details
            </summary>

            <pre className="overflow-x-auto p-4 bg-slate-950 text-slate-200 rounded-b-xl text-[11px] leading-relaxed">
              {JSON.stringify(result, null, 2)}
            </pre>

          </details>

          {/* HUMAN REVIEW */}

          <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-4">

            <div className="flex items-start gap-3">

              <ShieldAlert
                size={18}
                className="text-teal-700 mt-0.5"
              />

              <div className="flex-1">

                <h3 className="text-sm font-bold text-slate-900">
                  Safety Officer Review
                </h3>

                <p className="text-xs text-slate-600 mt-1">
                  AI assessment is decision support and does not
                  replace established safety procedures or Safety
                  Officer judgment.
                </p>

                <div className="flex flex-wrap gap-2 mt-4">

                  <button
                    type="button"
                    className="px-3 py-2 rounded-lg bg-[#004e47] text-white text-xs font-semibold hover:bg-[#08423d]"
                  >
                    Confirm Assessment
                  </button>

                  <button
                    type="button"
                    className="px-3 py-2 rounded-lg bg-white border border-gray-200 text-slate-700 text-xs font-semibold hover:bg-gray-50"
                  >
                    Correct Assessment
                  </button>

                  <button
                    type="button"
                    className="px-3 py-2 rounded-lg bg-white border border-gray-200 text-slate-700 text-xs font-semibold hover:bg-gray-50"
                  >
                    Request Further Review
                  </button>

                </div>

              </div>

            </div>

          </div>

        </div>
      )}

      {/* --------------------------------------------------- */}
      {/* BATCH RESULT */}
      {/* --------------------------------------------------- */}

      {batchResults && analysisMode === "file" && (
        <BatchResultsView
          data={batchResults}
        />
      )}

    </main>
  );
}

/* ========================================================= */
/* FINDING CARD */
/* ========================================================= */

function FindingCard({ title, value }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 min-h-[100px]">

      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
        {title}
      </span>

      <p className="mt-2 text-sm font-semibold text-slate-800 leading-relaxed">
        {value}
      </p>

    </div>
  );
}

/* ========================================================= */
/* REASONING STEP */
/* ========================================================= */

function ReasoningStep({ label }) {
  return (
    <span className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-semibold">
      {label}
    </span>
  );
}

/* ========================================================= */
/* BATCH RESULT VIEW */
/* ========================================================= */

function BatchResultsView({ data }) {
  /*
   * The exact /batch response shape depends on your FastAPI
   * implementation.
   *
   * This component therefore supports the common response
   * structures without creating fake classification values.
   */

  const evaluations =
    data?.evaluations ||
    data?.results ||
    data?.reports ||
    (Array.isArray(data) ? data : []);

  const total =
    data?.total ??
    evaluations.length;

  const highCount = evaluations.filter((item) => {
    const verdict = String(
      item?.verdict ||
        item?.sif_potential ||
        ""
    ).toLowerCase();

    return verdict.includes("high");
  }).length;

  const mediumCount = evaluations.filter((item) => {
    const verdict = String(
      item?.verdict ||
        item?.sif_potential ||
        ""
    ).toLowerCase();

    return verdict.includes("medium");
  }).length;

  return (
    <div className="rounded-2xl border border-gray-200/80 bg-white p-5 shadow-sm space-y-4">

      <div className="flex flex-wrap items-center justify-between border-b border-gray-100 pb-3 gap-2">

        <div className="flex items-center gap-2">

          <Zap
            className="text-[#00695c]"
            size={22}
          />

          <div>

            <h2 className="text-base font-bold text-gray-900">
              Batch Analysis Results
            </h2>

            <p className="text-xs text-gray-500">
              Results returned by the OILENS analysis engine
            </p>

          </div>

        </div>

        <span className="text-xs text-gray-400">
          {total} records processed
        </span>

      </div>

      {/* METRICS */}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">

        <div className="bg-gray-50 p-3 rounded-xl border border-gray-200">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">
            Total Records
          </span>

          <p className="text-xl font-black text-gray-800">
            {total}
          </p>
        </div>

        <div className="bg-red-50 p-3 rounded-xl border border-red-200">
          <span className="text-[11px] font-bold text-red-600 uppercase tracking-wider">
            High SIF Potential
          </span>

          <p className="text-xl font-black text-red-600">
            {highCount}
          </p>
        </div>

        <div className="bg-amber-50 p-3 rounded-xl border border-amber-200">
          <span className="text-[11px] font-bold text-amber-600 uppercase tracking-wider">
            Medium SIF Potential
          </span>

          <p className="text-xl font-black text-amber-600">
            {mediumCount}
          </p>
        </div>

      </div>

      {/* TABLE */}

      {evaluations.length > 0 ? (
        <div className="overflow-x-auto border border-gray-200 rounded-xl">

          <table className="w-full text-left text-xs">

            <thead className="bg-gray-50 border-b border-gray-200 font-bold text-gray-700">

              <tr>
                <th className="p-3">Report</th>
                <th className="p-3">Statement</th>
                <th className="p-3">Hazard</th>
                <th className="p-3">SIF Potential</th>
              </tr>

            </thead>

            <tbody className="divide-y divide-gray-100">

              {evaluations.map((item, index) => {

                const verdict =
                  item?.verdict ||
                  item?.sif_potential ||
                  "Analysis Complete";

                return (
                  <tr
                    key={index}
                    className="hover:bg-gray-50"
                  >

                    <td className="p-3 font-semibold text-slate-700">
                      {item?.report_id ||
                        `Record ${index + 1}`}
                    </td>

                    <td className="p-3 text-slate-700 max-w-md">
                      {item?.text ||
                        item?.statement ||
                        item?.report ||
                        "—"}
                    </td>

                    <td className="p-3 text-slate-600">
                      {item?.hazard ||
                        item?.detected_hazard ||
                        "Not identified"}
                    </td>

                    <td className="p-3">

                      <span
                        className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold ${getBatchVerdictClass(
                          verdict
                        )}`}
                      >
                        {formatVerdict(verdict)}
                      </span>

                    </td>

                  </tr>
                );
              })}

            </tbody>

          </table>

        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center">

          <FileText
            size={28}
            className="mx-auto text-gray-300"
          />

          <p className="mt-2 text-sm font-semibold text-gray-600">
            Analysis completed
          </p>

          <p className="mt-1 text-xs text-gray-400">
            The backend returned a response, but no batch result
            records were found in the expected fields.
          </p>

        </div>
      )}

    </div>
  );
}

/* ========================================================= */
/* BATCH HELPERS */
/* ========================================================= */

function formatVerdict(value) {
  const text = String(value || "");

  const lower = text.toLowerCase();

  if (lower.includes("high")) {
    return "HIGH SIF POTENTIAL";
  }

  if (lower.includes("medium")) {
    return "MEDIUM SIF POTENTIAL";
  }

  if (lower.includes("low")) {
    return "LOW SIF POTENTIAL";
  }

  return text;
}

function getBatchVerdictClass(value) {
  const lower = String(value || "").toLowerCase();

  if (lower.includes("high")) {
    return "bg-red-50 text-red-700 border-red-200";
  }

  if (lower.includes("medium")) {
    return "bg-amber-50 text-amber-700 border-amber-200";
  }

  if (lower.includes("low")) {
    return "bg-blue-50 text-blue-700 border-blue-200";
  }

  return "bg-slate-50 text-slate-700 border-slate-200";
}