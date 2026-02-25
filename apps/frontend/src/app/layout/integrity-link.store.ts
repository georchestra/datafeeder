import { Injectable, computed, signal } from '@angular/core'
import { IntegrityLinkResponse } from '../core/api/models'

@Injectable()
export class IntegrityLinkStore {
  integrityLink = signal<IntegrityLinkResponse | null>(null)
  intlinkId = signal<string | null>(null)

  /** Computed access level from the loaded integrity link. */
  accessLevel = computed(() => this.integrityLink()?.access_level ?? null)

  /** True if the current user is the dataset owner or an administrator. */
  isOwnerOrAdmin = computed(() => {
    const level = this.accessLevel()
    return level === 'OWNER' || level === 'ADMIN'
  })
}
