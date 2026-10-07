import React, { useCallback, useEffect, useState } from 'react';
import { getTranscriptions } from './api/client.js';
import UploadPanel from './components/UploadPanel.jsx';
import TranscriptionList from './components/TranscriptionList.jsx';

export default function App() {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [revision, setRevision] = useState(0);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  // Applied query is separate from draft input: typing alone never changes results.
  // Cancellation saves work; the guard also rejects late replies that ignore abort.
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true); setError('');
    getTranscriptions(query, controller.signal)
      .then((data) => { if (current) setRecords(data.transcriptions); })
      .catch((failure) => { if (current && failure.name !== 'AbortError') setError(failure.message); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [query, revision]);
  return (
    <main className="workspace">
      <header className="page-header"><div className="brand"><span className="brand-mark" aria-hidden="true">≋</span> AUDIO NOTES</div>
        <h1>From spoken to written.</h1><p>Turn recordings into text. Keep every conversation easy to find.</p></header>
      <div className="workspace-grid"><UploadPanel onSuccess={refresh} />
        <section className="results" aria-labelledby="results-title">
          <div className="results-heading"><div className="section-heading"><span className="step">02</span><h2 id="results-title">Your transcriptions</h2></div>
            <button type="button" className="text-button" onClick={refresh} disabled={loading}>Refresh</button></div>
          <form className="search-form" onSubmit={(event) => { event.preventDefault(); setQuery(draft.trim()); refresh(); }}>
            <label htmlFor="filename-search">Find a recording by filename</label><div className="search-controls">
              <input id="filename-search" type="search" value={draft} placeholder="e.g. Sample 1" onChange={(event) => setDraft(event.target.value)} />
              <button type="submit">Search</button>{(draft || query) && <button type="button" className="text-button" onClick={() => { setDraft(''); setQuery(''); refresh(); }}>Clear search</button>}
            </div></form>
          <p className="result-summary" role="status">{!loading && !error ? `${records.length} ${records.length === 1 ? 'recording' : 'recordings'}${query ? ` matching “${query}”` : ' · newest first'}` : ''}</p>
          <TranscriptionList records={records} loading={loading} error={error} query={query} onRetry={refresh} />
        </section>
      </div>
    </main>
  );
}
