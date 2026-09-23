const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function fetchApi(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    if (!response.ok) {
      const err = await response.text();
      console.error(`API Error ${response.status} on ${endpoint}:`, err);
      throw new Error(`API Error ${response.status}: ${err}`);
    }
    return response.json();
  } catch (e) {
    if (e.message.startsWith('API Error')) throw e;
    console.error(`Network error on ${endpoint}:`, e);
    throw e;
  }
}

// ----------------------------------------------------
// Existing Core Endpoints (Kept for compatibility)
// ----------------------------------------------------
export const checkHealth = () => fetchApi('/health');

export const analyseReport = (text, reportId = "", meta = {}) =>
  fetchApi('/analyse', { 
    method: 'POST', 
    body: JSON.stringify({ text, report_id: reportId, meta }) 
  });

export const analyseBatch = (reports) =>
  fetchApi('/batch', { 
    method: 'POST', 
    body: JSON.stringify(reports) 
  });

// ----------------------------------------------------
// New Integration Endpoints
// ----------------------------------------------------

// Queue (Triage)
export const getQueue = (page = 1, size = 50) => 
  fetchApi(`/api/queue?page=${page}&page_size=${size}`);

export const getQueueCounts = () => 
  fetchApi('/api/queue/counts');

// Review (Approvals/Overrides) — backend uses /{verdict_id}/action path
export const approveVerdict = (verdictId, reviewerId, note = null) =>
  fetchApi(`/api/review/${verdictId}/approve`, { 
    method: 'POST', 
    body: JSON.stringify({ reviewer_id: reviewerId, note: note || "" }) 
  });

export const correctVerdict = (verdictId, reviewerId, correctedVerdict, note = null) =>
  fetchApi(`/api/review/${verdictId}/correct`, { 
    method: 'POST', 
    body: JSON.stringify({ reviewer_id: reviewerId, corrected_verdict: correctedVerdict, note: note || "" }) 
  });

// Analytics (Dashboard)
export const getPatterns = (page = 1, size = 20) => 
  fetchApi(`/api/patterns?page=${page}&page_size=${size}`);

export const getSites = (page = 1, size = 20) => 
  fetchApi(`/api/sites?page=${page}&page_size=${size}`);

// Reports (List)
export const getReports = (page = 1, size = 50) => 
  fetchApi(`/api/reports?page=${page}&page_size=${size}`);

export const getReportDetail = (reportId) =>
  fetchApi(`/api/reports/${reportId}`);

// System
export const getSystemHealth = () => 
  fetchApi('/api/system/health');

export const getSystemModels = () => 
  fetchApi('/api/system/models');