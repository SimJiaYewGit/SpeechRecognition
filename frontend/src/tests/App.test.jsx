import React from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App.jsx';

const record = (id, name) => ({ id, original_filename: name, text: `Transcript ${id}`, created_at: '2026-10-01T08:30:00Z' });
const reply = (data, ok = true) => Promise.resolve({ ok, json: async () => data });
afterEach(() => vi.unstubAllGlobals());

test('renders stored filenames, text, and timestamps', async () => {
  vi.stubGlobal('fetch', vi.fn(() => reply({ transcriptions: [record(1, 'meeting.mp3')] })));
  render(<App />);
  expect(await screen.findByText('meeting.mp3')).toBeInTheDocument();
  expect(screen.getByText('Transcript 1')).toBeInTheDocument();
  expect(document.querySelector('time')).toHaveAttribute('datetime', '2026-10-01T08:30:00Z');
});

test('submits a batch sequentially, blocks duplicates, and continues after failure', async () => {
  const user = userEvent.setup();
  let finishFirst;
  const uploads = [];
  vi.stubGlobal('fetch', vi.fn((url, options) => {
    if (options?.method !== 'POST') return reply({ transcriptions: [] });
    uploads.push(options.body.get('file').name);
    if (uploads.length === 1) return new Promise((resolve) => { finishFirst = resolve; });
    if (uploads.length === 2) return reply({ error: { message: 'Invalid audio.' } }, false);
    return reply(record(3, 'third.mp3'));
  }));
  render(<App />);
  await user.upload(screen.getByLabelText('Choose audio files'), ['first', 'bad', 'third'].map((name) => new File(['audio'], `${name}.mp3`, { type: 'audio/mpeg' })));
  await user.click(screen.getByRole('button', { name: 'Transcribe recordings' }));
  expect(uploads).toEqual(['first.mp3']);
  expect(screen.getByRole('button', { name: 'Transcribing…' })).toBeDisabled();
  expect(screen.getByLabelText('Choose audio files')).toBeDisabled();
  await act(async () => { finishFirst({ ok: true, json: async () => record(1, 'first.mp3') }); });
  expect(await screen.findByText('2 completed, 1 failed.')).toBeInTheDocument();
  expect(uploads).toEqual(['first.mp3', 'bad.mp3', 'third.mp3']);
  expect(screen.getByText('Invalid audio.')).toBeInTheDocument();
});

test('searches filenames and clears back to all records', async () => {
  const user = userEvent.setup();
  const fetch = vi.fn((url) => reply({ transcriptions: url.startsWith('/search') ? [record(1, 'meeting.mp3')] : [record(1, 'meeting.mp3'), record(2, 'other.mp3')] }));
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  await screen.findByText('other.mp3');
  await user.type(screen.getByLabelText('Find a recording by filename'), ' meeting ');
  await user.click(screen.getByRole('button', { name: 'Search', exact: true }));
  await waitFor(() => expect(screen.queryByText('other.mp3')).not.toBeInTheDocument());
  expect(fetch).toHaveBeenCalledWith('/search?filename=meeting', expect.anything());
  await user.click(screen.getByRole('button', { name: 'Clear search' }));
  expect(await screen.findByText('other.mp3')).toBeInTheDocument();
});
