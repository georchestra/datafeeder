import { Component, inject } from '@angular/core'
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'

@Component({
  selector: 'app-intlink-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    NgIconComponent,
    TranslatePipe
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
