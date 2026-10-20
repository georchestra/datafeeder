import { bootstrapApplication } from '@angular/platform-browser'
import { loadAppConfig } from 'geonetwork-ui'
import { appConfig } from './app/app.config'
import { App } from './app/app'

loadAppConfig()
  .then(() => bootstrapApplication(App, appConfig))
  .catch((err) => console.error(err))
