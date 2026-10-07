import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.BACKEND_URL || 'http://127.0.0.1:5000';
  return {
    server: {
      proxy: Object.fromEntries(
        ['health', 'transcribe', 'transcriptions', 'search'].map((path) => [
          `^/${path}(?:\\?|$)`, { target, changeOrigin: true },
        ]),
      ),
    },
  };
});
