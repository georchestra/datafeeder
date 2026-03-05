import { Component, OnInit, inject, signal } from '@angular/core'
import {
  ActivatedRoute,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirRefreshCircle } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../core/api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../core/api/functions'
import { UiAlertBoxComponent } from '../shared/components/ui-alert-box/ui-alert-box.component'
import { IntegrityLinkStore } from './integrity-link.store'

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
    IntegrityLinkStore,
    provideIcons({
      iconoirRefreshCircle
    })
  ]
})
export class IntlinkLayoutComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)
  readonly store = inject(IntegrityLinkStore)

  loadError = signal<'forbidden' | 'not_found' | 'server_error' | null>(null)

  async ngOnInit(): Promise<void> {
    const intlinkId = this.route.snapshot.paramMap.get('intlink_id')
    this.store.intlinkId.set(intlinkId)
    if (intlinkId) {
      try {
        const integrityLink = await this.api.invoke(
          getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
          { integrity_link_id: intlinkId }
        )
        this.store.integrityLink.set(integrityLink)
      } catch (error: any) {
        console.error('Failed to load integrity link:', error)
        if (error?.status === 403) {
          this.loadError.set('forbidden')
        } else if (error?.status === 404) {
          this.loadError.set('not_found')
        } else {
          this.loadError.set('server_error')
        }
      }
    }
  }
}
