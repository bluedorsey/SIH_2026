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
  Clock,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Activity,
  Layers,
  MapPin,
} from "lucide-react";

import { analyseReport, analyseBatch } from "../../services/api";

export default function AnalyseStatementView() {
  const [analysisMode, setAnalysisMode] = useState("file");

  const [statement, setStatement] = useState("");
  const [site, setSite] = useState("All Sites");
  const [location, setLocation] = useState("");
  const [activity, setActivity] = useState("");

  const [uploadedFile, setUploadedFile] = useState(null);
  const [parsedData, setParsedData] = useState([]);
  const [fileError, setFileError] = useState("");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [batchResults, setBatchResults] = useState(null);
  const [apiError, setApiError] = useState("");

  const siteOptions = [
    "Duliajan",
    "Digboi",
    "Naharkatiya",
    "Moran",
    "Baghjan",
    "Rajasthan (Jodhpur)",
    "KG Basin",
  ];

  const examplePrompts = [
    {
      text: "Crane lifting 2 ton pipe over workers, sling was frayed and tag lines were missing.",
      site: "Duliajan Yard",
      location: "Workshop",
      activity: "Lifting Operations",
    },
    {
      text: "Monkey board se tool box neeche gira, barricading nahi tha aur derrick man bina harness ke tha.",
      site: "Rig #07 Digboi",
      location: "Derrick Floor",
      activity: "Drilling / Derrick Work",
    },
    {
      text: "Hot work near wellhead without gas test certificate or fire watch present.",
      site: "Wellhead #14 Naharkatiya",
      location: "Well Pad",
      activity: "Welding & Cutting",
    },
    {
      text: "AC ka remote kharab ho gaya canteen me, repair required.",
      site: "Central Canteen",
      location: "Staff Area",
      activity: "Facility Management",
    },
  ];

  // CSV PARSER

  const parseCSV = (csvText) => {
    const lines = csvText.split(/\r\n|\n/).filter((line) => line.trim() !== "");

    if (lines.length < 2) return [];

    const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());

    const statementIndex = headers.findIndex(
      (h) =>
        h.includes("statement") ||
        h.includes("report") ||
        h.includes("observation") ||
        h.includes("description") ||
        h.includes("text"),
    );

    const siteIndex = headers.findIndex(
      (h) => h.includes("site") || h.includes("location") || h.includes("yard"),
    );

    const activityIndex = headers.findIndex(
      (h) =>
        h.includes("activity") || h.includes("operation") || h.includes("work"),
    );

    const parsed = [];

    for (let i = 1; i < lines.length; i++) {
      const values =
        lines[i].match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || lines[i].split(",");

      const cleanValues = values.map((value) =>
        value.replace(/^"|"$/g, "").trim(),
      );

      const statementValue =
        statementIndex !== -1 ? cleanValues[statementIndex] : cleanValues[0];

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
              'Invalid JSON format. Expected an array containing objects with a "statement" or "text" field.',
            );
          } else {
            setParsedData(formatted);
          }
        } catch {
          setFileError(
            "Failed to parse JSON file. Please check the file syntax.",
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
        "Unsupported file format. Please upload a .csv or .json file.",
      );
      setUploadedFile(null);
    }
  };

  // SINGLE REPORT ANALYSIS

  const handleSingleAnalysis = async () => {
    if (!statement.trim() || loading) return;

    if (!site.trim() || !location.trim()) {
      setApiError(
        "Site and Location are compulsory fields. Please provide both to continue.",
      );
      return;
    }

    setLoading(true);
    setResult(null);
    setApiError("");

    try {
      const response = await analyseReport(statement.trim(), "", {
        site: site.trim(),
        location: location.trim(),
        activity: activity.trim(),
      });

      setResult(response);
    } catch (error) {
      console.error("OILENS analysis error:", error);

      setApiError(
        error?.message || "Unable to connect to the OILENS analysis engine.",
      );
    } finally {
      setLoading(false);
    }
  };

  // BATCH ANALYSIS

  const handleBatchAnalysis = async () => {
    if (parsedData.length === 0 || loading) return;

    setLoading(true);
    setBatchResults(null);
    setApiError("");

    try {
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

      setApiError(error?.message || "Unable to process the uploaded dataset.");
    } finally {
      setLoading(false);
    }
  };

  // MAIN ANALYSIS HANDLER

  const handleAnalyse = async () => {
    if (analysisMode === "text") {
      await handleSingleAnalysis();
    } else {
      await handleBatchAnalysis();
    }
  };

  // REMOVE FILE

  const removeFile = () => {
    setUploadedFile(null);
    setParsedData([]);
    setFileError("");
    setApiError("");
    setBatchResults(null);
  };

  // CTRL + ENTER

  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        handleAnalyse();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [statement, site, location, activity, parsedData, analysisMode, loading]);

  const isButtonDisabled =
    loading ||
    (analysisMode === "text" && !statement.trim()) ||
    (analysisMode === "file" && parsedData.length === 0);

  // UI

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
            Submit an unsafe-act, unsafe-condition, or near-miss report. OILENS
            extracts the relevant safety context and evaluates SIF potential
            using the analysis engine.
          </p>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Info size={14} />
            <span>
              AI assessment is decision support. Final review remains with the
              Safety Officer.
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
                    <span className="font-semibold text-gray-700">.CSV</span> or{" "}
                    <span className="font-semibold text-gray-700">.JSON</span>
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
                    {uploadedFile.name.toLowerCase().endsWith(".csv") ? (
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
                      {(uploadedFile.size / 1024).toFixed(1)} KB •{" "}
                      {parsedData.length} records detected
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="flex items-center gap-1 text-xs font-semibold text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg border border-rose-200"
                >
                  <X size={14} /> Remove File
                </button>
              </div>
            )}

            {fileError && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-600 font-medium">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <span>{fileError}</span>
              </div>
            )}

            {apiError && (
              <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-700">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Analysis engine unavailable</p>
                  <p className="mt-0.5">{apiError}</p>
                </div>
              </div>
            )}

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
                        <th className="p-2.5">Statement / Observation</th>
                        <th className="p-2.5">Site</th>
                        <th className="p-2.5">Activity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {parsedData.slice(0, 5).map((row, index) => (
                        <tr key={index} className="hover:bg-gray-50">
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
              <select
                value={site}
                onChange={(e) => {
                  setSite(e.target.value);
                  if (apiError.includes("compulsory fields")) setApiError("");
                }}
                className={`rounded-lg border px-3 py-1.5 text-xs text-gray-700 focus:border-teal-600 focus:outline-none sm:w-44 ${
                  !site.trim() && apiError.includes("compulsory fields")
                    ? "border-red-400 ring-1 ring-red-400"
                    : "border-gray-200"
                }`}
              >
                {siteOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Location (Required)*"
                value={location}
                onChange={(e) => {
                  setLocation(e.target.value);
                  if (apiError.includes("compulsory fields")) setApiError("");
                }}
                className={`rounded-lg border px-3 py-1.5 text-xs text-gray-700 placeholder-gray-400 focus:border-teal-600 focus:outline-none sm:w-64 ${!location.trim() && apiError.includes("compulsory fields") ? "border-red-400 ring-1 ring-red-400" : "border-gray-200"}`}
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
              <span className="text-xs text-gray-400">Try:</span>
              {examplePrompts.map((prompt, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    setStatement(prompt.text);
                    setSite(prompt.site || "");
                    setLocation(prompt.location || "");
                    setActivity(prompt.activity || "");
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
                  <p className="font-bold">Could not analyse the report</p>
                  <p className="mt-0.5">{apiError}</p>
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
                <Loader2 size={14} className="animate-spin" />
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

      {/* SINGLE RESULT (NEW UI) */}
      {result && analysisMode === "text" && (
        <SingleStatementResult result={result} />
      )}

      {/* BATCH RESULT */}
      {batchResults && analysisMode === "file" && (
        <BatchResultsView data={batchResults} />
      )}
    </main>
  );
}

/* ========================================================= */
/* SINGLE STATEMENT RESULT UI                                */
/* ========================================================= */

function SingleStatementResult({ result }) {
  const verdict = String(result?.verdict || "").toUpperCase();

  // Determine banner colors — bold filled backgrounds to match reference
  let bannerClass = "bg-slate-600 text-white";
  let verdictIcon = <HelpCircle size={24} className="text-white" />;

  if (["CAPACITY"].includes(verdict)) {
    bannerClass = "bg-gradient-to-r from-amber-600 to-orange-600 text-white";
    verdictIcon = <AlertTriangle size={24} className="text-white" />;
  } else if (
    ["H_SIF", "P_SIF", "L_SIF", "SIF", "HIGH SIF POTENTIAL"].includes(verdict)
  ) {
    bannerClass = "bg-gradient-to-r from-red-700 to-red-600 text-white";
    verdictIcon = <ShieldAlert size={24} className="text-white" />;
  } else if (["EXPOSURE"].includes(verdict)) {
    bannerClass = "bg-gradient-to-r from-yellow-600 to-amber-500 text-white";
    verdictIcon = <AlertCircle size={24} className="text-white" />;
  } else if (["SUCCESS", "NON_EVENT"].includes(verdict)) {
    bannerClass = "bg-gradient-to-r from-emerald-700 to-green-600 text-white";
    verdictIcon = <CheckCircle size={24} className="text-white" />;
  } else if (["LOW_ENERGY"].includes(verdict)) {
    bannerClass = "bg-gradient-to-r from-blue-700 to-blue-600 text-white";
    verdictIcon = <Info size={24} className="text-white" />;
  } else if (["INSUFFICIENT", "OUT_OF_SCOPE"].includes(verdict)) {
    bannerClass = "bg-gradient-to-r from-gray-600 to-gray-500 text-white";
    verdictIcon = <HelpCircle size={24} className="text-white" />;
  }

  const confidence = result?.verdict_detail?.confidence
    ? (result.verdict_detail.confidence * 100).toFixed(0) + "%"
    : "N/A";
  const processedTime = result?.provenance?.processed_at
    ? new Date(result.provenance.processed_at).toLocaleString()
    : "Unknown";

  const renderHighlightedText = () => {
    const text = result?.input?.text || "";
    const spans = result?.spans || [];

    // Sort spans by start index
    const sortedSpans = [...spans].sort((a, b) => a.start - b.start);

    if (sortedSpans.length === 0) return <span>{text}</span>;

    const elements = [];
    let lastIndex = 0;

    sortedSpans.forEach((span, idx) => {
      if (span.start > lastIndex) {
        elements.push(
          <span key={`text-${idx}`}>
            {text.substring(lastIndex, span.start)}
          </span>,
        );
      }

      let bgClass = "bg-gray-200";
      if (span.role === "energy_cue") bgClass = "bg-orange-200 text-orange-900";
      else if (span.role === "release_cue")
        bgClass = "bg-pink-200 text-pink-900";
      else if (span.role === "exposure_cue")
        bgClass = "bg-purple-200 text-purple-900";
      else if (span.role === "control_present")
        bgClass = "bg-green-200 text-green-900";
      else if (span.role === "control_absent")
        bgClass = "bg-red-200 text-red-900";
      else if (span.role === "control_ineffective")
        bgClass = "bg-yellow-200 text-yellow-900";
      else if (span.role === "outcome_cue")
        bgClass = "bg-gray-300 text-gray-900";
      else if (span.role === "negation_cue")
        bgClass = "bg-slate-300 text-slate-900";

      elements.push(
        <mark
          key={`span-${idx}`}
          className={`px-1 rounded font-medium ${bgClass}`}
          title={span.role}
        >
          {text.substring(span.start, span.end)}
        </mark>,
      );
      lastIndex = span.end;
    });

    if (lastIndex < text.length) {
      elements.push(<span key="text-end">{text.substring(lastIndex)}</span>);
    }

    return elements;
  };

  const getSpanColorClass = (role) => {
    if (role === "energy_cue")
      return "bg-orange-100 text-orange-800 border-orange-200";
    if (role === "release_cue")
      return "bg-pink-100 text-pink-800 border-pink-200";
    if (role === "exposure_cue")
      return "bg-purple-100 text-purple-800 border-purple-200";
    if (role === "control_present")
      return "bg-green-100 text-green-800 border-green-200";
    if (role === "control_absent")
      return "bg-red-100 text-red-800 border-red-200";
    if (role === "control_ineffective")
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    if (role === "outcome_cue")
      return "bg-gray-200 text-gray-800 border-gray-300";
    if (role === "negation_cue")
      return "bg-slate-200 text-slate-800 border-slate-300";
    return "bg-gray-100 text-gray-800 border-gray-200";
  };

  return (
    <div className="space-y-4">
      {/* 1. VERDICT BANNER */}
      <div
        className={`rounded-2xl p-5 sm:p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-md ${bannerClass}`}
      >
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-sm rounded-full">
            {verdictIcon}
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-80 mb-1">
              Verdict
            </p>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
              {verdict}
            </h2>
            <p className="text-sm font-medium opacity-90 capitalize">
              {verdict.replace(/_/g, " ").toLowerCase()} event
            </p>
          </div>
        </div>

        <div className="flex flex-col items-start md:items-center px-0 md:px-6 border-t md:border-t-0 md:border-l md:border-r border-white/20 py-3 md:py-0 w-full md:w-auto">
          <p className="text-xs font-bold uppercase tracking-wider opacity-80 mb-1">
            Confidence
          </p>
          <div className="text-2xl sm:text-3xl font-black">{confidence}</div>
          <div className="flex items-center gap-2 mt-1 text-[11px] font-semibold opacity-80">
            <span>Route: {result?.verdict_detail?.route || "Unknown"}</span>
            <span>•</span>
            <span>
              Layers: {(result?.verdict_detail?.layers_agreed || []).join(", ")}
            </span>
            <span>•</span>
            <span>Lang: {result?.meta?.language_detected || "Unknown"}</span>
          </div>
        </div>

        <div className="flex flex-col gap-2 items-start md:items-end w-full md:w-auto">
          {result?.review?.required && (
            <div className="bg-white/20 backdrop-blur-sm px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5">
              <Clock size={14} />
              <span>Human review: {result.review.reason}</span>
            </div>
          )}
          <div className="text-right mt-auto">
            <p className="text-xs font-bold opacity-80">{result?.report_id}</p>
            <p className="text-[10px] font-medium opacity-70 flex items-center gap-1 mt-0.5 justify-start md:justify-end">
              <Clock size={10} /> {processedTime}
            </p>
          </div>
        </div>
      </div>

      {/* 2. DECISION PATH */}
      {result?.verdict_detail?.decision_path && (
        <div className="bg-slate-800 text-slate-200 rounded-lg p-3 font-mono text-[11px] sm:text-xs overflow-x-auto whitespace-nowrap flex items-center gap-3">
          <span className="font-bold text-slate-400 shrink-0">
            DECISION PATH
          </span>
          <span className="text-slate-500">|</span>
          <span>{result.verdict_detail.decision_path.replace("->", "→")}</span>
        </div>
      )}

      {/* 3. EVIDENCE IN TEXT + THE FOUR QUESTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Evidence in Text */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
            <FileText size={16} className="text-teal-700" />
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wide">
              Evidence in Text
            </h3>
          </div>

          <div className="flex-1 bg-gray-50 rounded-lg p-4 border border-gray-100 text-sm md:text-base leading-relaxed text-gray-800 mb-4">
            {renderHighlightedText()}
          </div>

          <div>
            <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
              Detected Spans
            </h4>
            <div className="flex flex-wrap gap-2">
              {(result?.spans || []).map((span, idx) => (
                <div
                  key={idx}
                  className={`text-[11px] px-2 py-1 rounded-md border font-semibold flex items-center gap-1.5 ${getSpanColorClass(span.role)}`}
                >
                  <span className="opacity-75">
                    {span.role.replace(/_/g, " ")}:
                  </span>
                  <span>"{span.text}"</span>
                  <span className="opacity-50 text-[9px]">({span.source})</span>
                </div>
              ))}
              {(!result?.spans || result.spans.length === 0) && (
                <span className="text-xs text-gray-500 italic">
                  No specific spans detected.
                </span>
              )}
            </div>
          </div>
        </div>

        {/* The Four Questions */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
            <HelpCircle size={16} className="text-teal-700" />
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wide">
              The Four Questions (EEI)
            </h3>
          </div>

          <div className="space-y-4">
            {[
              { label: "High Energy Present", key: "high_energy_present" },
              { label: "Energy Released", key: "energy_released" },
              { label: "Serious Injury", key: "serious_injury" },
              {
                label: "Direct Control Present",
                key: "direct_control_present",
              },
            ].map((q) => {
              const fact = result?.eei_facts?.[q.key];
              if (!fact) return null;

              return (
                <div
                  key={q.key}
                  className="bg-gray-50 rounded-lg p-3 border border-gray-100"
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-bold text-gray-700">
                      {q.label}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${fact.value ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}
                    >
                      {fact.value ? "TRUE" : "FALSE"}
                    </span>
                  </div>
                  {fact.span && (
                    <div className="text-[11px] text-gray-500 italic flex justify-between items-end mt-2">
                      <span className="line-clamp-2">"{fact.span}"</span>
                      <span className="text-[9px] uppercase bg-gray-200 px-1.5 py-0.5 rounded ml-2 shrink-0">
                        {fact.source}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 4. BOTTOM THREE CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Safety Knowledge */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3 border-b border-gray-100 pb-2">
            <Layers size={15} className="text-teal-700" />
            <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
              Safety Knowledge
            </h3>
          </div>
          <div className="space-y-3 text-xs">
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Hazard</p>
              <p className="font-bold text-gray-900 capitalize">
                {(result?.safety_knowledge?.hazard || "Unknown").replace(
                  /_/g,
                  " ",
                )}
              </p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">
                Required Barrier
              </p>
              <p className="font-bold text-gray-900 capitalize">
                {(result?.safety_knowledge?.barrier || "Unknown").replace(
                  /_/g,
                  " ",
                )}
              </p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">LSR / Rules</p>
              <p className="font-bold text-gray-900">
                {(result?.safety_knowledge?.lsr || []).join(", ") || "None"}
              </p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">
                Potential Consequence
              </p>
              <p className="font-bold text-gray-900 capitalize">
                {(
                  result?.safety_knowledge?.potential_consequence || "Unknown"
                ).replace(/_/g, " ")}
              </p>
            </div>
          </div>
        </div>

        {/* Energy */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3 border-b border-gray-100 pb-2">
            <Zap size={15} className="text-teal-700" />
            <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
              Energy
            </h3>
          </div>
          <div className="space-y-3 text-xs">
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">Type</p>
              <p className="font-bold text-gray-900 capitalize">
                {(result?.energy?.type || "Unknown").replace(/_/g, " ")}
              </p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">
                Estimate (Joules)
              </p>
              <p className="font-bold text-gray-900">
                {result?.energy?.estimate_j !== null &&
                result?.energy?.estimate_j !== undefined
                  ? result.energy.estimate_j.toLocaleString()
                  : "—"}
              </p>
            </div>
            <div>
              <p className="font-semibold text-gray-500 mb-0.5">
                SIF Threshold (Joules)
              </p>
              <p className="font-bold text-gray-900">
                {result?.energy?.threshold_j !== null &&
                result?.energy?.threshold_j !== undefined
                  ? result.energy.threshold_j.toLocaleString()
                  : "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Unsafe Act / Condition */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3 border-b border-gray-100 pb-2">
              <Activity size={15} className="text-teal-700" />
              <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
                Unsafe Act / Condition
              </h3>
            </div>
            <div className="space-y-3 mt-4">
              {result?.uc_ua?.unsafe_act && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-3 py-2 rounded-lg font-bold text-sm flex items-center justify-between">
                  <span>Unsafe Act</span>
                  <Activity size={16} />
                </div>
              )}
              {result?.uc_ua?.unsafe_condition && (
                <div className="bg-orange-50 border border-orange-200 text-orange-800 px-3 py-2 rounded-lg font-bold text-sm flex items-center justify-between">
                  <span>Unsafe Condition</span>
                  <MapPin size={16} />
                </div>
              )}
              {!result?.uc_ua?.unsafe_act &&
                !result?.uc_ua?.unsafe_condition && (
                  <div className="bg-gray-50 border border-gray-200 text-gray-600 px-3 py-2 rounded-lg font-bold text-sm text-center">
                    None detected
                  </div>
                )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-gray-500">Confidence</span>
              <span className="font-bold text-gray-900">
                {result?.uc_ua?.confidence
                  ? (result.uc_ua.confidence * 100).toFixed(0) + "%"
                  : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center text-xs mt-1">
              <span className="font-semibold text-gray-500">Basis</span>
              <span className="font-bold text-gray-900 uppercase">
                {result?.uc_ua?.basis || "N/A"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ========================================================= */
/* BATCH RESULT VIEW */
/* ========================================================= */

function BatchResultsView({ data }) {
  const evaluations =
    data?.evaluations ||
    data?.results ||
    data?.reports ||
    (Array.isArray(data) ? data : []);

  const total = data?.total ?? evaluations.length;

  const highCount = evaluations.filter((item) => {
    const verdict = String(
      item?.verdict || item?.sif_potential || "",
    ).toLowerCase();

    return verdict.includes("high") || verdict.includes("h_sif");
  }).length;

  const mediumCount = evaluations.filter((item) => {
    const verdict = String(
      item?.verdict || item?.sif_potential || "",
    ).toLowerCase();

    return (
      verdict.includes("medium") ||
      verdict.includes("p_sif") ||
      verdict.includes("capacity")
    );
  }).length;

  return (
    <div className="rounded-2xl border border-gray-200/80 bg-white p-5 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between border-b border-gray-100 pb-3 gap-2">
        <div className="flex items-center gap-2">
          <Zap className="text-[#00695c]" size={22} />
          <div>
            <h2 className="text-base font-bold text-gray-900">
              Batch Analysis Results
            </h2>
            <p className="text-xs text-gray-500">
              Results returned by the OILENS analysis engine
            </p>
          </div>
        </div>
        <span className="text-xs text-gray-400">{total} records processed</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-gray-50 p-3 rounded-xl border border-gray-200">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">
            Total Records
          </span>
          <p className="text-xl font-black text-gray-800">{total}</p>
        </div>
        <div className="bg-red-50 p-3 rounded-xl border border-red-200">
          <span className="text-[11px] font-bold text-red-600 uppercase tracking-wider">
            High SIF Potential
          </span>
          <p className="text-xl font-black text-red-600">{highCount}</p>
        </div>
        <div className="bg-amber-50 p-3 rounded-xl border border-amber-200">
          <span className="text-[11px] font-bold text-amber-600 uppercase tracking-wider">
            Medium / Capacity Event
          </span>
          <p className="text-xl font-black text-amber-600">{mediumCount}</p>
        </div>
      </div>

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
                  item?.verdict || item?.sif_potential || "Analysis Complete";

                return (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-slate-700">
                      {item?.report_id || `Record ${index + 1}`}
                    </td>
                    <td className="p-3 text-slate-700 max-w-md">
                      {item?.text || item?.statement || item?.report || "—"}
                    </td>
                    <td className="p-3 text-slate-600">
                      {item?.hazard ||
                        item?.detected_hazard ||
                        "Not identified"}
                    </td>
                    <td className="p-3">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold ${getBatchVerdictClass(verdict)}`}
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
          <FileText size={28} className="mx-auto text-gray-300" />
          <p className="mt-2 text-sm font-semibold text-gray-600">
            Analysis completed
          </p>
          <p className="mt-1 text-xs text-gray-400">
            The backend returned a response, but no batch result records were
            found in the expected fields.
          </p>
        </div>
      )}
    </div>
  );
}

function formatVerdict(value) {
  const text = String(value || "");
  const lower = text.toLowerCase();
  if (lower.includes("high") || lower.includes("h_sif"))
    return "HIGH SIF POTENTIAL";
  if (
    lower.includes("medium") ||
    lower.includes("p_sif") ||
    lower.includes("capacity")
  )
    return "CAPACITY / P-SIF";
  if (lower.includes("low") || lower.includes("l_sif"))
    return "LOW SIF POTENTIAL";
  return text;
}

function getBatchVerdictClass(value) {
  const lower = String(value || "").toLowerCase();
  if (lower.includes("high") || lower.includes("h_sif"))
    return "bg-red-50 text-red-700 border-red-200";
  if (
    lower.includes("medium") ||
    lower.includes("p_sif") ||
    lower.includes("capacity")
  )
    return "bg-amber-50 text-amber-700 border-amber-200";
  if (lower.includes("low") || lower.includes("l_sif"))
    return "bg-blue-50 text-blue-700 border-blue-200";
  return "bg-slate-50 text-slate-700 border-slate-200";
}
