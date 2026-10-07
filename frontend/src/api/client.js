// Centralize JSON errors and avoid automatic retries: POST may have committed even
// when its response is lost. The UI tells users to inspect stored results first.
async function request(url, options = {}) {
  let response;
  try { response = await fetch(url, options); }
  catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error(options.method === 'POST'
      ? 'Connection lost. Refresh the transcription list before uploading again; the recording may have been saved.'
      : 'Could not reach the service. Check your connection and try again.');
  }
  let body;
  try { body = await response.json(); }
  catch { throw new Error('The service returned an unreadable response. Please refresh the list.'); }
  if (!response.ok) throw new Error(body.error?.message || `Request failed (${response.status}).`);
  return body;
}

export function getTranscriptions(query = '', signal) {
  return request(query ? `/search?filename=${encodeURIComponent(query)}` : '/transcriptions', { signal });
}

export function transcribeFile(file) {
  // Let the browser supply Content-Type with the matching multipart boundary.
  const data = new FormData();
  data.append('file', file);
  return request('/transcribe', { method: 'POST', body: data });
}
