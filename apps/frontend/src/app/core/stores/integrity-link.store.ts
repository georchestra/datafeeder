import { Injectable, inject, signal } from '@angular/core'
import { IntegrityLinkResponse } from '../api/models'
import { Api } from '../api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../api/functions'

@Injectable({ providedIn: 'root' })
export class IntegrityLinkStore {
  integrityLink = signal<IntegrityLinkResponse | null>(null)
  intlinkId = signal<string | null>(null)

  private api = inject(Api)

  async loadIntegrityLink(intlinkId: string): Promise<IntegrityLinkResponse> {
    const integrityLink = await this.api.invoke(
      getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
      { integrity_link_id: intlinkId }
    )

    this.intlinkId.set(intlinkId)
    this.integrityLink.set(integrityLink)

    return integrityLink
  }

  async setAndLoadIntegrityLink(
    intlinkId: string
  ): Promise<IntegrityLinkResponse> {
    this.intlinkId.set(intlinkId)
    return await this.loadIntegrityLink(intlinkId)
  }

  clearIntegrityLink(): void {
    this.intlinkId.set(null)
    this.integrityLink.set(null)
  }
}
