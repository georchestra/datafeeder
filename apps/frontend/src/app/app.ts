import { Component } from '@angular/core'
import { RouterModule } from '@angular/router'
import { getThemeConfig, ThemeService } from 'geonetwork-ui'

@Component({
  imports: [RouterModule],
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  constructor() {
    const theme = getThemeConfig()
    ThemeService.applyCssVariables(
      theme.PRIMARY_COLOR,
      theme.SECONDARY_COLOR,
      theme.MAIN_COLOR,
      theme.BACKGROUND_COLOR,
      theme.MAIN_FONT || 'Lato',
      theme.TITLE_FONT || 'Lato',
      theme.FONTS_STYLESHEET_URL
    )
    if (theme.FAVICON) ThemeService.setFavicon(theme.FAVICON)
  }
}
