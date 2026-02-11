import { Component } from '@angular/core'
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'

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
export class IntlinkLayoutComponent {}
