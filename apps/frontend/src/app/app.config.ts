import { provideHttpClient } from '@angular/common/http'
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection
} from '@angular/core'
import { provideRouter } from '@angular/router'
import { provideI18n, TRANSLATE_DEFAULT_CONFIG } from 'geonetwork-ui'
import { appRoutes } from './app.routes'
import { provideApiConfiguration } from './core/api/api-configuration'

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(appRoutes),
    provideHttpClient(),
    provideI18n(TRANSLATE_DEFAULT_CONFIG),
    provideApiConfiguration('/datakern-backend')
  ]
}
