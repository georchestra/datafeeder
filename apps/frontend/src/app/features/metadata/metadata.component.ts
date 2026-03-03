import { CommonModule } from '@angular/common'
import { Component, DestroyRef, effect, inject, OnInit, signal } from '@angular/core'
import { RouterLink } from '@angular/router'
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirNumber1Square,
  iconoirNumber2Square,
  iconoirNumber3Square
} from '@ng-icons/iconoir'
import { TranslateDirective, TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  DEFAULT_CONFIGURATION,
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface
} from 'geonetwork-ui'
import { combineLatest, firstValueFrom, from, interval, map, switchMap, take, takeWhile, tap } from 'rxjs'
import { Api } from '../../core/api/api'
import {
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
  getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
  getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet
} from '../../core/api/functions'
import { DagRunState } from '../../core/api/models'
import { IntegrityLinkStore } from '../../layout/integrity-link.store'

@Component({
  selector: 'app-metadata',
  imports: [
    CommonModule,
    NgIconComponent,
    ButtonComponent,
    TranslateDirective,
    TranslatePipe,
    RecordFormComponent,
    RouterLink
  ],
  templateUrl: './metadata.component.html',
  styleUrl: './metadata.component.css',
  host: { class: 'flex-1 min-h-0 flex flex-col overflow-y-auto' },
  providers: [
    provideIcons({
      iconoirNumber1Square,
      iconoirNumber2Square,
      iconoirNumber3Square
    })
  ]
})
export class MetadataComponent implements OnInit {
  private recordsRepository = inject(RecordsRepositoryInterface)
  protected editor = inject(EditorFacade)
  readonly store = inject(IntegrityLinkStore)
  private api = inject(Api)
  private destroyRef = inject(DestroyRef)

  processingStatus = signal<DagRunState | null>(null)
  processingStatusLoaded = signal(false)
  processingDagRunId = signal<string | null>(null)

  isRecordLoaded = toSignal(this.editor.record$.pipe(map((record) => !!record)))
  pages = toSignal(
    this.editor.editorConfig$.pipe(map((config) => config.pages))
  )
  currentPage$ = this.editor.currentPage$
  pagesLength$ = this.editor.editorConfig$.pipe(
    map((config) => config.pages.length)
  )
  isLastPage$ = combineLatest([this.currentPage$, this.pagesLength$]).pipe(
    map(([currentPage, pagesCount]) => currentPage >= pagesCount - 1)
  )

  constructor() {
    effect(() => {
      const integrityLink = this.store.integrityLink()
      if (integrityLink?.metadata_id) {
        this.loadMetadata(integrityLink.metadata_id)
      } else if (integrityLink && !integrityLink.metadata_id && !this.processingStatusLoaded()) {
        this.loadProcessingStatus(integrityLink.id)
      }
    })
  }

  ngOnInit(): void {
    const customConfig = DEFAULT_CONFIGURATION
    // Keep only the ANNEXES_SECTION in the resources page
    customConfig.pages[1].sections = [
      DEFAULT_CONFIGURATION.pages[1].sections[1]
    ]
    this.editor.setConfiguration(customConfig)
  }

  private loadMetadata(metadataId: string): void {
    try {
      this.recordsRepository
        .openRecordForEdition(metadataId)
        .pipe(
          take(1),
          tap(([currentRecord, currentRecordSource]) => {
            this.editor.openRecord(currentRecord, currentRecordSource)
          })
        )
        .subscribe()
    } catch (error) {
      console.error('Error loading metadata:', error)
    }
  }

  private async loadProcessingStatus(intlinkId: string): Promise<void> {
    try {
      const response = await this.api.invoke(
        getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
        { dag_id: 'process_dag', intlink_id: intlinkId, limit: 1 }
      )

      const latestRun = response.dag_runs[0] ?? null
      if (!latestRun) {
        this.processingStatusLoaded.set(true)
        return
      }

      this.processingDagRunId.set(latestRun.dag_run_id)
      this.processingStatus.set(latestRun.state)
      this.processingStatusLoaded.set(true)

      if (latestRun.state === 'queued' || latestRun.state === 'running') {
        this.startPollingStatus(intlinkId, latestRun.dag_run_id)
      }
    } catch (error) {
      console.error('Error loading processing status:', error)
      this.processingStatusLoaded.set(true)
    }
  }

  private startPollingStatus(intlinkId: string, dagRunId: string): void {
    interval(2000)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        switchMap(() =>
          from(
            this.api.invoke(getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet, {
              dag_id: 'process_dag',
              dag_run_id: dagRunId
            })
          )
        ),
        takeWhile(
          (status: DagRunState) => status === 'queued' || status === 'running',
          true
        )
      )
      .subscribe({
        next: async (status: DagRunState) => {
          this.processingStatus.set(status)
          if (status === 'success') {
            await this.reloadIntegrityLink(intlinkId)
          }
        },
        error: (error) => console.error('Error polling processing status:', error)
      })
  }

  private async reloadIntegrityLink(intlinkId: string): Promise<void> {
    try {
      const updated = await this.api.invoke(
        getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
        { integrity_link_id: intlinkId }
      )
      this.store.integrityLink.set(updated)
    } catch (error) {
      console.error('Error reloading integrity link:', error)
    }
  }

  pageSectionClickHandler(index: number) {
    this.editor.setCurrentPage(index)
  }

  isCurrentPage(index: number) {
    return this.editor.currentPage$.pipe(
      map((currentPage) => currentPage === index)
    )
  }

  async previousPageButtonHandler() {
    const currentPage = await firstValueFrom(this.currentPage$)
    this.editor.setCurrentPage(currentPage - 1)
    window.scroll({
      top: 0
    })
  }

  async nextPageButtonHandler() {
    const currentPage = await firstValueFrom(this.currentPage$)
    this.editor.setCurrentPage(currentPage + 1)
    window.scroll({
      top: 0
    })
  }
}
