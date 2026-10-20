import {
  ConfigIssues,
  fetchConfig,
  parseThemeSection,
  parseTranslationsSection,
  reportConfigIssues,
  setAppConfig
} from 'geonetwork-ui'

/**
 * Loads the default.toml configuration, reading only the sections used by datafeeder.
 * The sections are then available through the geonetwork-ui getters (getThemeConfig, etc.)
 */
export function loadAppConfig(): Promise<void> {
  return fetchConfig().then((parsed) => {
    const issues: ConfigIssues = { warnings: [], errors: [] }
    const theme = parseThemeSection(parsed, issues)
    const translations = parseTranslationsSection(parsed)
    reportConfigIssues(issues)
    setAppConfig({ theme, translations })
  })
}
