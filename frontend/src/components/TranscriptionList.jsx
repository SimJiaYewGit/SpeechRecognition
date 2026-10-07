import React from 'react';

export default function TranscriptionList({ records, loading, error, query, onRetry }) {
  // JSX escapes filenames and model output; never interpret transcript text as HTML.
  return <div aria-busy={loading}>
    {loading ? <p className="empty-state" role="status">Loading transcriptions…</p>
      : error ? <div className="error-box" role="alert"><p>{error}</p><button type="button" onClick={onRetry}>Try again</button></div>
      : !records.length ? <div className="empty-state"><span className="empty-symbol" aria-hidden="true">≡</span>
        <h3>{query ? 'No matching recordings' : 'Your words, ready to read'}</h3>
        <p>{query ? `No filenames contain “${query}”. Try another name or clear the search.` : 'Upload your first recording to see its transcription here.'}</p>
      </div>
      : <ul className="transcription-list" aria-label="Transcriptions">{records.map((record) => <li key={record.id}>
        <article className="transcription-card"><div className="record-meta"><span className="record-label">TRANSCRIPT</span>
          <time dateTime={record.created_at}>{new Date(record.created_at).toLocaleString()}</time></div>
          <h3>{record.original_filename}</h3><p className="transcript-text">{record.text || 'No speech was recognized in this recording.'}</p>
        </article>
      </li>)}</ul>}
  </div>;
}
