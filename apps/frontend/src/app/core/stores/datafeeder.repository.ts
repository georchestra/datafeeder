import { inject, Injectable } from '@angular/core'
import { Gn4Repository, markRecordAsChanged } from 'geonetwork-ui'
import { Observable, of } from 'rxjs'
import { IntegrityLinkStore } from './integrity-link.store'
import { Store } from '@ngrx/store'

@Injectable({
  providedIn: 'root'
})
export class DatafeederRepository extends Gn4Repository {
  private editorStore = inject(Store)
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

  setRecordFlag(
    uniqueIdentifier: string,
    flagName: 'IS_REFERENCE_DATASET',
    value: boolean
  ): Observable<void> {
    if (flagName !== 'IS_REFERENCE_DATASET') {
      throw new Error(`Unknown record flag: ${flagName}`)
    }
    this.store.integrityLink.update((intLink) => ({
      ...intLink,
      is_reference_dataset: value
    }))
    this.store.isReferenceDatasetChanged.set(true)
    this.editorStore.dispatch(markRecordAsChanged())
    return of(undefined)
  }
}
