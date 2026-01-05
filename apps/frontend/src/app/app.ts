import { Component } from '@angular/core'
import { RouterModule } from '@angular/router'
import { ThemeService } from 'geonetwork-ui'

@Component({
  imports: [RouterModule],
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'frontend'

  constructor() {
    ThemeService.applyCssVariables(
      '#E30513',
      '#007A80',
      '#212029',
      'white',
      'Lato'
    )
  }
}
