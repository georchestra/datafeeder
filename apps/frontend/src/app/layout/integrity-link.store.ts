import { Injectable, signal } from '@angular/core'
import { IntegrityLinkResponse } from '../core/api/models'

@Injectable()
export class IntegrityLinkStore {
  integrityLink = signal<IntegrityLinkResponse | null>(null)
  intlinkId = signal<string | null>(null)
}
