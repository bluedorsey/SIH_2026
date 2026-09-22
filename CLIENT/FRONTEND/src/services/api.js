const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json();
}

export async function analyseReport(
  text,
  reportId = "",
  meta = {}
) {
  const response = await fetch(`${API_BASE_URL}/analyse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      report_id: reportId,
      meta,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Analysis failed (${response.status}): ${errorText}`
    );
  }

  return response.json();
}

export async function analyseBatch(reports) {
  const response = await fetch(`${API_BASE_URL}/batch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(reports),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Batch analysis failed (${response.status}): ${errorText}`
    );
  }

  return response.json();
}