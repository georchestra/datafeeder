import { bootstrapApplication } from '@angular/platform-browser'
import { loadAppConfig } from 'geonetwork-ui'
import { appConfig } from './app/app.config'
import { App } from './app/app'

loadAppConfig(undefined, ['theme', 'translations'])
  .then(() => bootstrapApplication(App, appConfig))
  .catch((err) => console.error(err))
