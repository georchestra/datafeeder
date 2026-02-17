import { Component, OnInit, inject } from '@angular/core'
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
import { IntegrityLinkStore } from './integrity-link.store'

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

  async ngOnInit(): Promise<void> {
    const intlinkId = this.route.snapshot.paramMap.get('intlink_id')
    this.store.intlinkId.set(intlinkId)
    if (intlinkId) {
      const integrityLink = await this.api.invoke(
        getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
        { integrity_link_id: intlinkId }
      )
      this.store.integrityLink.set(integrityLink)
    }
  }
}
