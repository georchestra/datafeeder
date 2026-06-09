import { CommonModule } from '@angular/common'
import {
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  OnInit,
  signal,
  TemplateRef,
  untracked,
  viewChild
} from '@angular/core'
import { RouterLink } from '@angular/router'
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirNumber1Square,
  iconoirNumber2Square,
  iconoirNumber3Square,
  iconoirRefreshCircle,
  iconoirOpenNewWindow
} from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  DEFAULT_CONFIGURATION,
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface,
  SpinningLoaderComponent
} from 'geonetwork-ui'
import {
  combineLatest,
  firstValueFrom,
  from,
  interval,
  map,
  switchMap,
  take,
  takeWhile,
  tap
} from 'rxjs'
import { Api } from '../../core/api/api'
import {
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
  getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
  getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet
} from '../../core/api/functions'
import { TaskStatus } from '../../core/api/models'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { FooterService } from '../../core/layout/footer.service'
import { IntlinkNavService } from '../../core/layout/intlink-nav.service'
import { MetadataSaveService } from '../../core/layout/metadata-save.service'
import { SettingsService } from '../../core/settings/settings.service'
import { AiGenerateButtonComponent } from './ai-generate-button.component'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

marker('metadata.processing.queued')
marker('metadata.processing.running')
marker('footer.previous')
marker('footer.openInCatalogue')
marker('footer.saveAndOpenInCatalogue')
marker('footer.next.resources')
marker('footer.next.accessAndContact')
marker('footer.next.recurrence')
marker('footer.next.events')
marker('footer.next.authorizations')
marker('footer.saveAndNext.recurrence')
marker('footer.saveAndNext.events')
marker('footer.saveAndNext.authorizations')
marker('editor.record.form.bottomButtons.next')

const PAGE_KEY_RESOURCES = 'editor.record.form.page.resources'
const PAGE_KEY_ACCESS_CONTACT = 'editor.record.form.page.accessAndContact'

@Component({
  selector: 'app-metadata',
  imports: [
    CommonModule,
    NgIconComponent,
    ButtonComponent,
    TranslatePipe,
    RecordFormComponent,
    RouterLink,
    SpinningLoaderComponent,
    AiGenerateButtonComponent
  ],
  templateUrl: './metadata.component.html',
  styleUrl: './metadata.component.css',
  host: { class: 'flex-1 min-h-0 flex flex-col overflow-y-auto' },
  providers: [
    provideIcons({
      iconoirNumber1Square,
      iconoirNumber2Square,
      iconoirNumber3Square,
      iconoirRefreshCircle,
      iconoirOpenNewWindow
    })
  ]
})
export class MetadataComponent implements OnInit {
  private recordsRepository = inject(RecordsRepositoryInterface)
  protected editor = inject(EditorFacade)
  readonly store = inject(IntegrityLinkStore)
  readonly metadataSaveService = inject(MetadataSaveService)
  private navService = inject(IntlinkNavService)
  private footerService = inject(FooterService)
  private destroyRef = inject(DestroyRef)
  private api = inject(Api)
  private settingsService = inject(SettingsService)

  aiMetadataEnabled = computed(() => {
    const features =
      this.settingsService.getSetting<string[]>('enabled_features')
    return features?.includes('ai_metadata') ?? false
  })

  readonly footerTpl = viewChild<TemplateRef<unknown>>('footerTpl')

  processingStatus = signal<TaskStatus | null>(null)
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
  isLastFormPage = toSignal(this.isLastPage$, { initialValue: false })
  currentPageSignal = toSignal(this.currentPage$, { initialValue: 0 })
  changedSinceSave = toSignal(this.editor.changedSinceSave$, {
    initialValue: false
  })

  readonly nextIntlinkRoute = computed(() => this.navService.nextRoute('edit'))

  readonly catalogueUrl = computed(() =>
    this.navService.catalogueUrl(this.store.integrityLink()?.metadata_id)
  )

  readonly nextButtonLabelKey = computed(() => {
    if (!this.isLastFormPage()) {
      const nextPageIndex = this.currentPageSignal() + 1
      const pageKey = this.pages()?.[nextPageIndex]?.labelKey
      if (pageKey === PAGE_KEY_RESOURCES) return 'footer.next.resources'
      if (pageKey === PAGE_KEY_ACCESS_CONTACT)
        return 'footer.next.accessAndContact'
      return 'editor.record.form.bottomButtons.next'
    }
    const changed = this.changedSinceSave()
    const next = this.nextIntlinkRoute()
    if (next) {
      const base = this.navService.nextRouteLabel(next)
      return changed
        ? base.replace('footer.next.', 'footer.saveAndNext.')
        : base
    }
    return changed ? 'footer.saveAndOpenInCatalogue' : 'footer.openInCatalogue'
  })

  constructor() {
    effect(() => {
      const integrityLink = this.store.integrityLink()
      if (integrityLink && !this.processingStatusLoaded()) {
        this.loadProcessingStatus(integrityLink.id)
      }
    })

    effect(() => {
      const tpl = this.footerTpl()
      untracked(() => this.footerService.setContent(tpl ?? null))
    })

    this.destroyRef.onDestroy(() => this.footerService.setContent(null))
  }

  ngOnInit(): void {
    // Keep only the ANNEXES_SECTION in the resources page
    const resourcesPage = DEFAULT_CONFIGURATION.pages[1]
    const pages = [...DEFAULT_CONFIGURATION.pages]
    pages[1] = {
      ...resourcesPage,
      sections: resourcesPage.sections.slice(1, 2)
    }
    this.editor.setConfiguration({ ...DEFAULT_CONFIGURATION, pages })
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
        const integrityLink = this.store.integrityLink()
        if (integrityLink?.metadata_id) {
          this.processingStatus.set('success')
          this.loadMetadata(integrityLink.metadata_id)
        }
        return
      }

      this.processingDagRunId.set(latestRun.dag_run_id)
      this.processingStatus.set(latestRun.state)
      this.processingStatusLoaded.set(true)

      if (latestRun.state === 'success') {
        const integrityLink = this.store.integrityLink()
        if (integrityLink?.metadata_id) {
          this.loadMetadata(integrityLink.metadata_id)
        }
      } else if (
        latestRun.state === 'queued' ||
        latestRun.state === 'running'
      ) {
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
            this.api.invoke(
              getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
              {
                dag_id: 'process_dag',
                dag_run_id: dagRunId
              }
            )
          )
        ),
        takeWhile(
          (response: TaskStatus) =>
            response === 'queued' || response === 'running',
          true
        )
      )
      .subscribe({
        next: async (response: TaskStatus) => {
          this.processingStatus.set(response)
          if (response === 'success') {
            await this.reloadIntegrityLink(intlinkId)
            const integrityLink = this.store.integrityLink()
            if (integrityLink?.metadata_id) {
              this.loadMetadata(integrityLink.metadata_id)
            }
          }
        },
        error: (error) =>
          console.error('Error polling processing status:', error)
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
    window.scroll({ top: 0 })
  }

  async nextPageButtonHandler() {
    const currentPage = await firstValueFrom(this.currentPage$)
    this.editor.setCurrentPage(currentPage + 1)
    window.scroll({ top: 0 })
  }

  async saveAndNavigateNext(): Promise<void> {
    const intlinkId = this.store.intlinkId()
    const next = this.nextIntlinkRoute()
    if (!intlinkId || !next) return
    if (this.changedSinceSave()) {
      await this.metadataSaveService.save()
    }
    this.navService.navigate(intlinkId, next)
  }

  async saveAndOpenCatalogue(): Promise<void> {
    if (this.changedSinceSave()) {
      await this.metadataSaveService.save()
    }
    this.navService.openCatalogue(this.store.integrityLink()?.metadata_id)
  }

  onReconfigureClick(): Promise<void> {
    return this.navService.reconfigure()
  }
}
