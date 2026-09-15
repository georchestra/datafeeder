/// <reference types='vitest' />
import { defineConfig } from 'vite';
import angular from '@analogjs/vite-plugin-angular';

export default defineConfig(() => ({
  root: __dirname,
  cacheDir: './node_modules/.vite/frontend',
  plugins: [angular()],
  // Uncomment this if you are using workers.
  // worker: {
  //  plugins: [ nxViteTsPaths() ],
  // },
  test: {
    name: 'frontend',
    watch: false,
    globals: true,
    environment: 'jsdom',
    include: ['{src,tests}/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    setupFiles: ['src/test-setup.ts'],
    reporters: ['default'],
    // Dev machine is RAM-constrained; parallel workers cause OOM segfaults.
    fileParallelism: false,
    pool: 'forks',
    poolOptions: { forks: { maxForks: 1 } },
    coverage: {
      reportsDirectory: './coverage/frontend',
      provider: 'v8' as const,
    },
  },
}));
