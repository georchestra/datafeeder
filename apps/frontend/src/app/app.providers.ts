import { Provider } from '@angular/core'
import { getGlobalConfig, provideRepositoryUrl } from 'geonetwork-ui'

/**
 * Providers whose values come from the default.toml configuration,
 * loaded with loadAppConfig() before bootstrap (see main.ts)
 */
export const APP_CONFIG_PROVIDERS: Provider[] = [
  provideRepositoryUrl(() => getGlobalConfig().GN4_API_URL)
]
