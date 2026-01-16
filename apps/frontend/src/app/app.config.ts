import { provideHttpClient } from '@angular/common/http'
import {
  ApplicationConfig,
  importProvidersFrom,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection
} from '@angular/core'
import { provideRouter } from '@angular/router'
import {
  FeatureEditorModule,
  provideGn4,
  provideI18n,
  provideRepositoryUrl,
  TRANSLATE_DEFAULT_CONFIG
} from 'geonetwork-ui'
import { appRoutes } from './app.routes'
import { provideApiConfiguration } from './core/api/api-configuration'
import { StoreModule } from '@ngrx/store'
import { EffectsModule } from '@ngrx/effects'

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(appRoutes),
    provideHttpClient(),
    provideI18n(TRANSLATE_DEFAULT_CONFIG),
    provideRepositoryUrl(() => '/datakern-backend/geonetwork/srv/api'),
    provideGn4(),
    importProvidersFrom(
      StoreModule.forRoot(
        {},
        {
          metaReducers: [],
          runtimeChecks: {
            strictActionImmutability: false,
            strictStateImmutability: false
          }
        }
      )
    ),
    importProvidersFrom(EffectsModule.forRoot()),
    importProvidersFrom(FeatureEditorModule),
    provideApiConfiguration('/datakern-backend')
  ]
}
