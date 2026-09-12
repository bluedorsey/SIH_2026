export type RiskLevel = "HIGH" | "REVIEW" | "ROUTINE";

export interface Report {
  id: string;
  priority: RiskLevel;
  title: string;
  activity: string;
  hazard: string;
  barrierFailure: string;
  lsr: string;
  site: string;
  confidence: number;
  reportedAgo: string;
  reportType: string;
  location: string;
  reportedBy: string;
  date: string;
  originalText: string;
}

export interface Pattern {
  id: string;
  title: string;
  occurrences: number;
  sites: string[];
  lsr: string;
  trend: number;
  riskLevel: RiskLevel;
}

export interface SiteData {
  name: string;
  reports: number;
  sifPotential: number;
  density: number;
  trend: "up" | "flat" | "down";
  risk: RiskLevel;
}

export const reports: Report[] = [
  {
    id: "OIL-2026-00482",
    priority: "HIGH",
    title: "Suspended load without banksman",
    activity: "Lifting Operation",
    hazard: "Suspended load",
    barrierFailure: "Banksman absent",
    lsr: "Lifting Operations",
    site: "Duliajan",
    confidence: 96,
    reportedAgo: "2h ago",
    reportType: "Near Miss",
    location: "Compressor Area",
    reportedBy: "Field Observation",
    date: "09 Sep 2026",
    originalText:
      "During lifting operation, load was suspended and no banksman was present. The crane operator proceeded without establishing exclusion zone around the lift area.",
  },
  {
    id: "OIL-2026-00479",
    priority: "HIGH",
    title: "Technician entered vessel before gas test",
    activity: "Confined Space",
    hazard: "Hazardous atmosphere",
    barrierFailure: "Atmospheric testing not completed",
    lsr: "Confined Space",
    site: "Digboi",
    confidence: 93,
    reportedAgo: "4h ago",
    reportType: "Unsafe Act",
    location: "Processing Unit",
    reportedBy: "Supervisor Report",
    date: "09 Sep 2026",
    originalText:
      "Technician entered vessel without completing mandatory gas test. Permit to work was issued but atmospheric testing step was bypassed due to time pressure.",
  },
  {
    id: "OIL-2026-00475",
    priority: "HIGH",
    title: "Energy isolation not verified before maintenance",
    activity: "Energy Isolation",
    hazard: "Stored energy release",
    barrierFailure: "Lockout/Tagout incomplete",
    lsr: "Energy Isolation",
    site: "Naharkatiya",
    confidence: 91,
    reportedAgo: "6h ago",
    reportType: "Unsafe Condition",
    location: "Wellhead",
    reportedBy: "Field Observation",
    date: "09 Sep 2026",
    originalText:
      "Maintenance work commenced on pressurized line without confirming all isolation points were locked out. Partial LOTO applied but not verified by second person.",
  },
  {
    id: "OIL-2026-00471",
    priority: "HIGH",
    title: "Worker positioned in line of fire during pipe break",
    activity: "Line Breaking",
    hazard: "Pressurized fluid release",
    barrierFailure: "Line of fire not cleared",
    lsr: "Line of Fire",
    site: "Duliajan",
    confidence: 89,
    reportedAgo: "8h ago",
    reportType: "Near Miss",
    location: "Pipeline Corridor",
    reportedBy: "HSE Patrol",
    date: "09 Sep 2026",
    originalText:
      "During line breaking operation on hydrocarbon line, two workers positioned directly in front of flange. Residual pressure present. No deflection shield in place.",
  },
  {
    id: "OIL-2026-00468",
    priority: "REVIEW",
    title: "Hot work started near hydrocarbon line",
    activity: "Hot Work",
    hazard: "Ignition source",
    barrierFailure: "Isolation / gas testing unclear",
    lsr: "Hot Work",
    site: "Bokakhat",
    confidence: 71,
    reportedAgo: "10h ago",
    reportType: "Unsafe Act",
    location: "Storage Area",
    reportedBy: "Field Observation",
    date: "09 Sep 2026",
    originalText:
      "Hot work permit issued and work commenced near hydrocarbon line. Gas testing was noted on permit but extent of isolation zone was not clearly documented.",
  },
  {
    id: "OIL-2026-00463",
    priority: "REVIEW",
    title: "Worker on elevated platform without fall arrest",
    activity: "Working at Height",
    hazard: "Fall from height",
    barrierFailure: "Fall arrest not connected",
    lsr: "Working at Height",
    site: "Duliajan",
    confidence: 68,
    reportedAgo: "1d ago",
    reportType: "Unsafe Act",
    location: "Workshop",
    reportedBy: "Supervisor Report",
    date: "08 Sep 2026",
    originalText:
      "Worker observed on scaffold at approximately 4.5m height. Fall arrest harness was worn but lifeline not connected to anchor point. Work area was not barricaded.",
  },
  {
    id: "OIL-2026-00459",
    priority: "REVIEW",
    title: "Simultaneous operations not coordinated",
    activity: "Energy Isolation",
    hazard: "Multiple energy sources",
    barrierFailure: "SIMOPS coordination failure",
    lsr: "Energy Isolation",
    site: "Digboi",
    confidence: 64,
    reportedAgo: "1d ago",
    reportType: "Near Miss",
    location: "Processing Unit",
    reportedBy: "Shift Supervisor",
    date: "08 Sep 2026",
    originalText:
      "Two separate maintenance activities occurring in adjacent areas without formal SIMOPS coordination. Energy sources in shared corridor may not have been fully isolated.",
  },
  {
    id: "OIL-2026-00452",
    priority: "ROUTINE",
    title: "PPE not worn correctly during routine inspection",
    activity: "Routine Inspection",
    hazard: "Minor exposure",
    barrierFailure: "PPE compliance",
    lsr: "Personal Protective Equipment",
    site: "Naharkatiya",
    confidence: 94,
    reportedAgo: "2d ago",
    reportType: "Unsafe Act",
    location: "Wellhead",
    reportedBy: "Field Observation",
    date: "07 Sep 2026",
    originalText:
      "Inspector observed without safety glasses during walkdown. Hard hat worn but chin strap not fastened. Hi-vis vest worn correctly. No immediate hazard exposure at time of observation.",
  },
  {
    id: "OIL-2026-00449",
    priority: "ROUTINE",
    title: "Housekeeping issues in workshop area",
    activity: "Workshop Activity",
    hazard: "Slip/trip hazard",
    barrierFailure: "Housekeeping standards",
    lsr: "Personal Protective Equipment",
    site: "Bokakhat",
    confidence: 88,
    reportedAgo: "2d ago",
    reportType: "Unsafe Condition",
    location: "Workshop",
    reportedBy: "HSE Patrol",
    date: "07 Sep 2026",
    originalText:
      "Workshop floor had oil spill near lathe machine area. Spill kit available but not deployed. Trip hazard from loose cable near workbench. No immediate injury.",
  },
  {
    id: "OIL-2026-00445",
    priority: "ROUTINE",
    title: "Vehicle speed limit exceeded in yard",
    activity: "Vehicle Operations",
    hazard: "Vehicle collision",
    barrierFailure: "Speed compliance",
    lsr: "Driving",
    site: "Duliajan",
    confidence: 91,
    reportedAgo: "3d ago",
    reportType: "Unsafe Act",
    location: "Site Yard",
    reportedBy: "CCTV Review",
    date: "06 Sep 2026",
    originalText:
      "Service vehicle recorded at 34 km/h in 20 km/h zone near pedestrian crossing. No pedestrians present at time of incident. Driver identity confirmed from vehicle log.",
  },
];

export const patterns: Pattern[] = [
  {
    id: "PAT-001",
    title: "Isolation not verified before maintenance",
    occurrences: 27,
    sites: ["Duliajan", "Digboi", "Naharkatiya"],
    lsr: "Energy Isolation",
    trend: 18,
    riskLevel: "HIGH",
  },
  {
    id: "PAT-002",
    title: "Personnel entering lifting exclusion zones",
    occurrences: 19,
    sites: ["Duliajan", "Bokakhat"],
    lsr: "Lifting Operations",
    trend: 12,
    riskLevel: "HIGH",
  },
  {
    id: "PAT-003",
    title: "Gas testing incomplete before confined-space entry",
    occurrences: 14,
    sites: ["Digboi", "Naharkatiya"],
    lsr: "Confined Space",
    trend: 9,
    riskLevel: "REVIEW",
  },
  {
    id: "PAT-004",
    title: "Hot work permit conditions not fully verified",
    occurrences: 11,
    sites: ["Bokakhat", "Duliajan"],
    lsr: "Hot Work",
    trend: 5,
    riskLevel: "REVIEW",
  },
  {
    id: "PAT-005",
    title: "Fall arrest not connected at height",
    occurrences: 9,
    sites: ["Duliajan", "Digboi"],
    lsr: "Working at Height",
    trend: -3,
    riskLevel: "REVIEW",
  },
  {
    id: "PAT-006",
    title: "Line of fire not cleared before pressurized operations",
    occurrences: 8,
    sites: ["Duliajan"],
    lsr: "Line of Fire",
    trend: 22,
    riskLevel: "HIGH",
  },
  {
    id: "PAT-007",
    title: "Banksman unavailable during crane operations",
    occurrences: 7,
    sites: ["Duliajan", "Naharkatiya"],
    lsr: "Lifting Operations",
    trend: 8,
    riskLevel: "HIGH",
  },
];

export const siteData: SiteData[] = [
  { name: "Duliajan", reports: 184, sifPotential: 52, density: 28.3, trend: "up", risk: "HIGH" },
  { name: "Digboi", reports: 126, sifPotential: 31, density: 24.6, trend: "up", risk: "HIGH" },
  { name: "Bokakhat", reports: 97, sifPotential: 16, density: 16.5, trend: "flat", risk: "REVIEW" },
  { name: "Naharkatiya", reports: 81, sifPotential: 9, density: 11.1, trend: "down", risk: "ROUTINE" },
  { name: "Jorhat", reports: 58, sifPotential: 6, density: 10.3, trend: "flat", risk: "ROUTINE" },
  { name: "Sivasagar", reports: 44, sifPotential: 4, density: 9.1, trend: "down", risk: "ROUTINE" },
];

export const trendData = [
  { month: "Jan", total: 38, sif: 7 },
  { month: "Feb", total: 42, sif: 9 },
  { month: "Mar", total: 51, sif: 11 },
  { month: "Apr", total: 47, sif: 10 },
  { month: "May", total: 55, sif: 14 },
  { month: "Jun", total: 61, sif: 16 },
  { month: "Jul", total: 68, sif: 18 },
  { month: "Aug", total: 74, sif: 19 },
  { month: "Sep", total: 64, sif: 14 },
];

export const activityData = [
  { name: "Lifting Operations", value: 34, sifCount: 40 },
  { name: "Energy Isolation", value: 21, sifCount: 25 },
  { name: "Confined Space", value: 16, sifCount: 19 },
  { name: "Hot Work", value: 13, sifCount: 15 },
  { name: "Working at Height", value: 9, sifCount: 11 },
  { name: "Line Breaking", value: 7, sifCount: 8 },
];

export const lsrData = [
  { name: "Energy Isolation", sifCount: 31, total: 58, density: 53.4, trend: 8, topFailure: "LOTO incomplete" },
  { name: "Lifting Operations", sifCount: 28, total: 52, density: 53.8, trend: 12, topFailure: "Banksman absent" },
  { name: "Confined Space", sifCount: 19, total: 44, density: 43.2, trend: 9, topFailure: "Gas test skipped" },
  { name: "Hot Work", sifCount: 16, total: 39, density: 41.0, trend: 5, topFailure: "Gas test incomplete" },
  { name: "Line of Fire", sifCount: 14, total: 31, density: 45.2, trend: 22, topFailure: "Exclusion zone not set" },
  { name: "Working at Height", sifCount: 11, total: 28, density: 39.3, trend: -3, topFailure: "Fall arrest unconnected" },
  { name: "Driving", sifCount: 6, total: 19, density: 31.6, trend: -7, topFailure: "Speed compliance" },
  { name: "PPE", sifCount: 3, total: 52, density: 5.8, trend: -2, topFailure: "Correct PPE not worn" },
];

export const lsrIcons: Record<string, string> = {
  "Energy Isolation": "⚡",
  "Lifting Operations": "🏗️",
  "Confined Space": "🔒",
  "Hot Work": "🔥",
  "Line of Fire": "🎯",
  "Working at Height": "🧗",
  "Driving": "🚗",
  "PPE": "🦺",
};

export const notifications = [
  {
    id: 1,
    level: "HIGH",
    title: "New critical precursor detected",
    body: "Three lifting-related SIF precursors were reported at Duliajan within the last 24 hours.",
    time: "12 min ago",
  },
  {
    id: 2,
    level: "REVIEW",
    title: "Emerging pattern",
    body: "Energy isolation failures increased 22% this month compared to prior 30-day period.",
    time: "1h ago",
  },
  {
    id: 3,
    level: "REVIEW",
    title: "Review required",
    body: "8 reports have AI confidence below 70% and require human classification.",
    time: "3h ago",
  },
  {
    id: 4,
    level: "HIGH",
    title: "Site risk score elevated",
    body: "Digboi site risk score increased to 71/100. Confined space precursors trending upward.",
    time: "6h ago",
  },
];
