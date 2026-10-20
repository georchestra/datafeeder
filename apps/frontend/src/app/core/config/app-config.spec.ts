import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  _reset,
  getCustomTranslations,
  getGlobalConfig,
  getThemeConfig
} from 'geonetwork-ui'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadAppConfig } from './app-config'

function stubConfigFile(toml: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, text: () => Promise.resolve(toml) })
  )
}

describe('loadAppConfig', () => {
  afterEach(() => {
    _reset()
    vi.unstubAllGlobals()
  })

  it('loads the default.toml shipped with the app', async () => {
    stubConfigFile(
      readFileSync(resolve(__dirname, '../../../../conf/default.toml'), 'utf-8')
    )
    await loadAppConfig()
    expect(getThemeConfig().PRIMARY_COLOR).toBe('#E30513')
  })

  it('does not require nor load a [global] section', async () => {
    stubConfigFile(`
[theme]
primary_color = "#111111"
secondary_color = "#222222"
main_color = "#333333"
background_color = "#444444"

[translations.en]
my.key = "My value"
`)
    await loadAppConfig()
    expect(getThemeConfig().PRIMARY_COLOR).toBe('#111111')
    expect(getCustomTranslations('en')).toEqual({ 'my.key': 'My value' })
    expect(() => getGlobalConfig()).toThrow()
  })

  it('fails if a mandatory theme color is missing', async () => {
    stubConfigFile(`
[theme]
primary_color = "#111111"
`)
    await expect(loadAppConfig()).rejects.toThrow(
      'mandatory settings were missing'
    )
  })
})
