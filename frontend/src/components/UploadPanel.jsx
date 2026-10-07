import React, { useRef, useState } from 'react';
import { transcribeFile } from '../api/client.js';

export default function UploadPanel({ onSuccess }) {
  const [files, setFiles] = useState([]);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState('');
  // A ref closes the double-submit window before React renders disabled controls.
  const active = useRef(false);
  const input = useRef(null);

  function selectFiles(event) {
    setFiles(Array.from(event.target.files).map((file, id) => {
      const error = !/\.mp3$/i.test(file.name) ? 'Choose an MP3 file.' : !file.size ? 'This file is empty.' : '';
      return { id, file, status: error ? 'failed' : 'queued', error };
    }));
    setSummary('');
  }

  async function submit(event) {
    event.preventDefault();
    if (active.current || !files.some((item) => item.status === 'queued')) return;
    active.current = true;
    setRunning(true);
    setSummary('');
    let completed = 0;
    let failed = files.filter((item) => item.status === 'failed').length;
    const update = (id, changes) => setFiles((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item));
    try {
      // Deliberately await each request: the backend accepts one inference at a time.
      // Keep each failure local to its file so the remaining batch can continue.
      for (const item of files.filter((entry) => entry.status === 'queued')) {
        update(item.id, { status: 'processing' });
        try {
          await transcribeFile(item.file);
          update(item.id, { status: 'completed' });
          completed += 1;
          onSuccess();
        } catch (error) {
          update(item.id, { status: 'failed', error: error.message });
          failed += 1;
        }
      }
      setSummary(`${completed} completed${failed ? `, ${failed} failed` : ''}.`);
    } finally { active.current = false; setRunning(false); }
  }

  return <section className="panel" aria-labelledby="upload-title">
    <div className="section-heading"><span className="step">01</span><h2 id="upload-title">Add recordings</h2></div>
    <p className="muted">Choose one recording or a batch. We’ll transcribe them one at a time.</p>
    <form onSubmit={submit}>
      <div className="file-picker">
        <span className="upload-symbol" aria-hidden="true">↑</span>
        <label htmlFor="audio-files">Choose audio files</label>
        <p id="file-help">MP3 files · single or multiple recordings</p>
        <input ref={input} id="audio-files" type="file" accept=".mp3,audio/mpeg" multiple disabled={running}
          aria-describedby="file-help" onChange={selectFiles} />
      </div>
      {files.length > 0 && <ul className="queue" aria-label="Selected recordings">{files.map((item) => <li key={item.id}>
        <div className="file-row"><span className="filename">{item.file.name}</span><span className={`badge ${item.status}`}>{item.status}</span></div>
        <span className="file-size">{(item.file.size / 1024).toFixed(1)} KB</span>
        {item.error && <p className="error-text">{item.error}</p>}
      </li>)}</ul>}
      <div className="actions"><button className="primary" disabled={running || !files.some((item) => item.status === 'queued')}>
        {running ? 'Transcribing…' : 'Transcribe recordings'}</button>
        {files.length > 0 && <button type="button" className="text-button" disabled={running} onClick={() => {
          setFiles([]); setSummary(''); input.current.value = '';
        }}>Clear files</button>}
      </div>
    </form>
    <p className="batch-status" role="status">{running ? `${files.filter((item) => item.status === 'completed').length} of ${files.length} completed. Processing recordings…` : summary}</p>
  </section>;
}
