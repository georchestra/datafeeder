import { Component, inject } from '@angular/core'
import { NgTemplateOutlet } from '@angular/common'
import { RouterOutlet } from '@angular/router'
import { OperationToastComponent } from '../shared/components/operation-toast/operation-toast.component'
import { FooterService } from '../core/layout/footer.service'

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, OperationToastComponent, NgTemplateOutlet],
  templateUrl: './main-layout.component.html'
})
export class MainLayoutComponent {
  protected footerService = inject(FooterService)
}
