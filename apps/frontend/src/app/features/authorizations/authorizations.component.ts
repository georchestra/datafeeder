import { Component, OnInit, inject, signal } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../../core/api/functions'
import { IntegrityLinkResponse } from '../../core/api/models'

@Component({
  selector: 'app-authorizations',
  imports: [TranslatePipe],
  templateUrl: './authorizations.component.html'
})
export class AuthorizationsComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)

  intlinkId = this.route.parent?.snapshot.paramMap.get('intlink_id') ?? null
  integrityLink = signal<IntegrityLinkResponse | null>(null)

  ngOnInit(): void {
    if (this.intlinkId) {
      this.loadIntegrityLink(this.intlinkId)
    }
  }

  private async loadIntegrityLink(id: string): Promise<void> {
    const metadata = await this.api.invoke(
      getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
      { integrity_link_id: id }
    )
    this.integrityLink.set(metadata)
  }
}
