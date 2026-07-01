import { Injectable, computed, inject, signal } from '@angular/core'
import { ImportType, IntegrityLinkResponse } from '../api/models'
import { Api } from '../api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../api/functions'

export const EMPTY_IMPORT_TYPE: ImportType = 'empty'
export const PREFILLED_IMPORT_TYPE: ImportType = 'prefilled'

@Injectable({ providedIn: 'root' })
export class IntegrityLinkStore {
  integrityLink = signal<IntegrityLinkResponse | null>(null)
  intlinkId = signal<string | null>(null)
  loadError = signal<'forbidden' | 'not_found' | 'server_error' | null>(null)

  private api = inject(Api)

  /** Computed access level from the loaded integrity link. */
  accessLevel = computed(() => this.integrityLink()?.access_level ?? null)

  /** True if the current user is the dataset owner or an administrator. */
  isOwnerOrAdmin = computed(() => {
    const level = this.accessLevel()
    return level === 'OWNER' || level === 'ADMIN'
  })

  /** True when the dataset has no source data (created as empty). */
  isEmptyDataset = computed(
    () => this.integrityLink()?.source_import_type === EMPTY_IMPORT_TYPE
  )

  /** True when the dataset references pre-existing data inserted directly in the DB. */
  isPrefilledDataset = computed(
    () => this.integrityLink()?.source_import_type === PREFILLED_IMPORT_TYPE
  )

  /**
   * True when the dataset originates from a remote source (url, database, api,
   * ftp) — i.e. neither a file imported from the user's machine nor an empty
   * or prefilled dataset. Recurrence scheduling is only relevant for these.
   */
  isRemoteDataset = computed(() => {
    const type = this.integrityLink()?.source_import_type
    return (
      type != null &&
      type !== 'file' &&
      type !== EMPTY_IMPORT_TYPE &&
      type !== PREFILLED_IMPORT_TYPE
    )
  })

  async loadIntegrityLink(intlinkId: string): Promise<IntegrityLinkResponse> {
    try {
      const integrityLink = await this.api.invoke(
        getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
        { integrity_link_id: intlinkId }
      )

      this.intlinkId.set(intlinkId)
      this.integrityLink.set(integrityLink)
      this.loadError.set(null)

      return integrityLink
    } catch (error: any) {
      console.error('Failed to load integrity link:', error)
      if (error?.status === 403) {
        this.loadError.set('forbidden')
      } else if (error?.status === 404) {
        this.loadError.set('not_found')
      } else {
        this.loadError.set('server_error')
      }

      return Promise.reject(error)
    }
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
