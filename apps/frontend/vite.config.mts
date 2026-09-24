/// <reference types='vitest' />
import { defineConfig } from 'vite'
import angular from '@analogjs/vite-plugin-angular'

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
    // Needed while on the geonetwork-ui dev prerelease (geonetwork/geonetwork-ui#1734):
    // it pulls in an extensionless `ol/format/WFS` import that vitest can't externalize.
    // Re-check once we're back on a stable geonetwork-ui release.
    server: { deps: { inline: ['geonetwork-ui'] } },
    reporters: ['default'],
    // RAM-constrained dev machines OOM with parallel workers; keep CI parallel.
    ...(process.env.CI
      ? {}
      : {
          fileParallelism: false,
          pool: 'forks' as const,
          poolOptions: { forks: { maxForks: 1 } }
        }),
    coverage: {
      reportsDirectory: './coverage/frontend',
      provider: 'v8' as const
    }
  }
}))
