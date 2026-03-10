import { Component, inject } from '@angular/core'
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { UiAlertBoxComponent } from '../shared/components/ui-alert-box/ui-alert-box.component'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

marker('intlinkLayout.error.forbidden.message')
marker('intlinkLayout.error.forbidden.title')
marker('intlinkLayout.error.not_found.message')
marker('intlinkLayout.error.not_found.title')
marker('intlinkLayout.error.server_error.message')
marker('intlinkLayout.error.server_error.title')

@Component({
  selector: 'app-intlink-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    NgIconComponent,
    TranslatePipe,
    UiAlertBoxComponent
  ],
  templateUrl: './intlink-layout.component.html',
  providers: [
    provideIcons({
      iconoirRefreshCircle
    })
  ]
})
export class IntlinkLayoutComponent {
  readonly store = inject(IntegrityLinkStore)
}
