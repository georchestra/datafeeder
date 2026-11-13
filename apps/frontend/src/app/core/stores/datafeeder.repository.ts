import { inject, Injectable } from '@angular/core'
import { Gn4Repository } from 'geonetwork-ui'
import { from, Observable, of } from 'rxjs'
import { Api } from '../api/api'
import { updateIsReferenceIngestionIntegrityLinkIntegrityLinkIdIsReferencePatch } from '../api/functions'
import { IntegrityLinkStore } from './integrity-link.store'

@Injectable({
  providedIn: 'root'
})
export class DatafeederRepository extends Gn4Repository {
  private api = inject(Api)
  private store = inject(IntegrityLinkStore)

  // we're reading flags from the datafeeder backend
  getRecordFlag(
    uniqueIdentifier: string,
    flagName: 'IS_REFERENCE_DATASET'
  ): Observable<boolean> {
    if (flagName !== 'IS_REFERENCE_DATASET') {
      throw new Error(`Unknown record flag: ${flagName}`)
    }
    return of(this.store.integrityLink().is_reference_dataset)
  }

  // we're writing flags only to the datafeeder backend
  setRecordFlag(
    uniqueIdentifier: string,
    flagName: 'IS_REFERENCE_DATASET',
    value: boolean
  ): Observable<void> {
    if (flagName !== 'IS_REFERENCE_DATASET') {
      throw new Error(`Unknown record flag: ${flagName}`)
    }
    const promise = this.api
      .invoke(
        updateIsReferenceIngestionIntegrityLinkIntegrityLinkIdIsReferencePatch,
        {
          integrity_link_id: this.store.integrityLink().id,
          body: { is_reference: value }
        }
      )
      .then(() => {
        this.store.integrityLink.update((intLink) => ({
          ...intLink,
          is_reference_dataset: value
        }))
      })
    return from(promise)
  }
}
