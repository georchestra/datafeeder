import { bootstrapApplication } from '@angular/platform-browser'
import { appConfig } from './app/app.config'
import { App } from './app/app'
import { loadAppConfig } from './app/core/config/app-config'

loadAppConfig()
  .then(() => bootstrapApplication(App, appConfig))
  .catch((err) => console.error(err))
