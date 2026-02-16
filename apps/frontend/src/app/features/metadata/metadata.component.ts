import { CommonModule } from '@angular/common'
import { Component, effect, inject } from '@angular/core'
import { toSignal } from '@angular/core/rxjs-interop'
import {
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface
} from 'geonetwork-ui'
import { map, take, tap } from 'rxjs'
import { IntegrityLinkStore } from '../../layout/integrity-link.store'

@Component({
  selector: 'app-metadata',
  imports: [CommonModule, RecordFormComponent],
  templateUrl: './metadata.component.html',
  styleUrl: './metadata.component.css',
  host: { class: 'flex-1 min-h-0 flex flex-col overflow-y-auto' }
})
export class MetadataComponent {
  private recordsRepository = inject(RecordsRepositoryInterface)
  protected editor = inject(EditorFacade)
  readonly store = inject(IntegrityLinkStore)

  isRecordLoaded = toSignal(this.editor.record$.pipe(map((record) => !!record)))

  constructor() {
    effect(() => {
      const integrityLink = this.store.integrityLink()
      if (integrityLink) {
        this.loadMetadata(integrityLink.metadata_id)
      }
    })
  }

  private loadMetadata(metadataId: string): void {
    try {
      this.recordsRepository
        .openRecordForEdition(metadataId)
        .pipe(
          take(1),
          tap(([currentRecord, currentRecordSource]) => {
            this.editor.openRecord(currentRecord, currentRecordSource)
            // TODO: remove when navigation between pages is implemented
            this.editor.setCurrentPage(0)
          })
        )
        .subscribe()
    } catch (error) {
      console.error('Error loading metadata:', error)
    }
  }
}
