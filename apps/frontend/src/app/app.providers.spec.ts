import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { FactoryProvider } from '@angular/core'
import { _reset, getThemeConfig, loadAppConfig } from 'geonetwork-ui'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { APP_CONFIG_PROVIDERS } from './app.providers'

describe('APP_CONFIG_PROVIDERS', () => {
  beforeEach(async () => {
    // load the default.toml shipped with the app
    const toml = readFileSync(
      resolve(__dirname, '../../conf/default.toml'),
      'utf-8'
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, text: () => Promise.resolve(toml) })
    )
    await loadAppConfig()
  })

  afterEach(() => {
    _reset()
    vi.unstubAllGlobals()
  })

  it('parses the default configuration', () => {
    expect(getThemeConfig().PRIMARY_COLOR).toBe('#E30513')
  })

  it('provides the repository URL from the [global] section', () => {
    const repositoryUrlProvider = APP_CONFIG_PROVIDERS[0] as FactoryProvider
    expect(repositoryUrlProvider.useFactory().basePath).toBe(
      '/datafeeder-backend/geonetwork/srv/api'
    )
  })
})
