const API_BASE = window.location.origin;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API 失败: ${response.status}`);
  }
  return response.json();
}

export async function searchItems(query, top_k = 50) {
  return request('/learning/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k }),
  });
}

export async function askQuestion(question, top_k = 10) {
  return request('/learning/ask', {
    method: 'POST',
    body: JSON.stringify({ question, top_k }),
  });
}

export async function runWorkflow() {
  return request('/learning/run', { method: 'POST' });
}

export async function submitFeedback(item_id, open_id, action) {
  return request('/learning/feedback', {
    method: 'POST',
    body: JSON.stringify({ item_id, open_id, action }),
  });
}

export async function fetchSeries(series_id) {
  return request('/learning/series', {
    method: 'POST',
    body: JSON.stringify({ series_id }),
  });
}

export async function fetchFeedRecommendations() {
  return request('/learning/feed-recommendations');
}

