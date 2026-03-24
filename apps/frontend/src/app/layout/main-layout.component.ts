import { Component } from '@angular/core'
import { RouterOutlet } from '@angular/router'
import { ErrorToastComponent } from '../shared/components/error-toast/error-toast.component'

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, ErrorToastComponent],
  templateUrl: './main-layout.component.html'
})
export class MainLayoutComponent {}
