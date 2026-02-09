import { CommonModule } from '@angular/common'
import { Component, OnInit, inject } from '@angular/core'
import { toSignal } from '@angular/core/rxjs-interop'
import { ActivatedRoute } from '@angular/router'
import {
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface
} from 'geonetwork-ui'
import { map, take, tap } from 'rxjs'
import { Api } from '../../core/api/api'
import { getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet } from '../../core/api/functions'
import { IntegrityLinkResponse } from '../../core/api/models'

@Component({
  selector: 'app-metadata',
  imports: [CommonModule, RecordFormComponent],
  templateUrl: './metadata.component.html',
  styleUrl: './metadata.component.css'
})
export class MetadataComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)
  private recordsRepository = inject(RecordsRepositoryInterface)
  protected editor = inject(EditorFacade)

  intlink_id: string | null = null

  isRecordLoaded = toSignal(this.editor.record$.pipe(map((record) => !!record)))

  ngOnInit(): void {
    this.intlink_id = this.route.snapshot.paramMap.get('intlink_id')
    if (this.intlink_id) {
      this.loadMetadata(this.intlink_id)
    }
  }

  private async loadMetadata(intlink_id: string): Promise<void> {
    try {
      const response: IntegrityLinkResponse = await this.api.invoke(
        getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
        {
          integrity_link_id: intlink_id
        }
      )

      this.recordsRepository
        .openRecordForEdition(response.metadata_id)
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
