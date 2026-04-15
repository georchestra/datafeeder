import { Component } from '@angular/core'
import { RouterOutlet } from '@angular/router'
import { OperationToastComponent } from '../shared/components/operation-toast/operation-toast.component'

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, OperationToastComponent],
  templateUrl: './main-layout.component.html'
})
export class MainLayoutComponent {}
