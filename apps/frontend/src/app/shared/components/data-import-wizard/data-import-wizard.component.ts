import { HttpErrorResponse } from '@angular/common/http'
import {
  Component,
  computed,
  effect,
  inject,
  signal,
  OnInit
} from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { MatButtonToggleModule } from '@angular/material/button-toggle'
import { MatTabsModule } from '@angular/material/tabs'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { Router, ActivatedRoute } from '@angular/router'
import {
  iconoirMap,
  iconoirNumber1Square,
  iconoirNumber2Square,
  iconoirTable,
  iconoirWarningTriangle,
  iconoirXmark
} from '@ng-icons/iconoir'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { ButtonComponent, SpinningLoaderComponent } from 'geonetwork-ui'
import {
  Subject,
  catchError,
  debounceTime,
  from,
  interval,
  lastValueFrom,
  of,
  switchMap,
  takeWhile,
  throwError,
  timeout
} from 'rxjs'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { Api } from '../../../core/api/api'
import {
  getStagingMetadataIngestionStagingIntegrityLinkIdMetadataGet,
  getStagingPreviewIngestionStagingIntegrityLinkIdPreviewGet,
  getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
  submitStagingIngestionStagingPost,
  processStagingDataIngestionProcessPost,
  editStagingMetadataIngestionStagingIntegrityLinkIdMetadataPut
} from '../../../core/api/functions'
import type {
  ColumnConfigInput,
  DagRunState,
  ForceProjection,
  StagingResponse,
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import type { SourceData } from '../data-source-selector/data-source-selector.component'
import { DataSourceSelectorComponent } from '../data-source-selector/data-source-selector.component'
import { DatasetTitleComponent } from '../dataset-title/dataset-title.component'
import { DatasetConfigurationComponent } from '../dataset-configuration/dataset-configuration.component'
import type {
  ColumnAction,
  CastType
} from '../column-action-menu/column-action-menu.component'
import type { ColumnFilter } from '../../../core/api/models/column-filter'
import { DatasetPreviewTableComponent } from '../dataset-preview-table/dataset-preview-table.component'
import { DatasetPreviewMapComponent } from '../dataset-preview-map/dataset-preview-map.component'
import { UiAlertBoxComponent } from '../ui-alert-box/ui-alert-box.component'

marker('import.dataSource.error')
marker('import.dataSource.error.extent')
marker('i18nerror.transformation.geometry_creation_failed')
marker('i18nerror.transformation.columns_both_required')
marker('i18nerror.transformation.projection_application_failed')
marker('import.metadataPublication.error')

const POLL_INTERVAL_MS = 500
const MAX_POLL_TIME_MS = 120000

/* eslint-disable no-unused-vars */
const enum ImportStatus {
  QUEUED = 'queued',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILED = 'failed'
}
/* eslint-enable no-unused-vars */

export interface ImportWizardData {
  source: SourceData
}

@Component({
  selector: 'app-data-import-wizard',
  imports: [
    MatButtonToggleModule,
    MatTabsModule,
    NgIconComponent,
    ButtonComponent,
    SpinningLoaderComponent,
    DataSourceSelectorComponent,
    DatasetTitleComponent,
    DatasetConfigurationComponent,
    TranslatePipe,
    DatasetPreviewTableComponent,
    DatasetPreviewMapComponent,
    UiAlertBoxComponent
  ],
  templateUrl: './data-import-wizard.component.html',
  styleUrls: ['./data-import-wizard.component.scss'],
  providers: [
    provideIcons({
      iconoirMap,
      iconoirNumber1Square,
      iconoirNumber2Square,
      iconoirTable,
      iconoirWarningTriangle,
      iconoirXmark
    })
  ]
})
export class DataImportWizardComponent implements OnInit {
  private api = inject(Api)
  private translate = inject(TranslateService)
  private router = inject(Router)
  private route = inject(ActivatedRoute)

  private renameSubject = new Subject<{
    originalName: string
    newName: string
  }>()

  selectedTabIndex = signal(0)
  importData = signal<ImportWizardData>(null)

  importing = signal(false)
  polling = signal(false)
  importError = signal<string | null>(null)
  metadata = signal<StagingMetadataResponse | null>(null)
  preview = signal<StagingPreviewResponse | null>(null)
  previewError = signal<string | null>(null)
  previewErrorExtent = signal<string | null>(null)
  previewLoading = signal<boolean>(false)
  dagRunInfo = signal<{ dag_id: string; dag_run_id: string } | null>(null)
  integrityLinkId = signal<string | null>(null)
  processing = signal(false)
  validationError = signal<string | null>(null)
  previewTabIndex = signal(0)
  hasExtentError = signal(false)

  columnConfigs = signal<ColumnConfigInput[]>([])
  forceProjection = signal<ForceProjection | null>(null)
  configSaving = signal(false)

  columnNameErrors = signal<Set<string>>(new Set())
  hasColumnNameError = computed(() => this.columnNameErrors().size > 0)

  isGeographicData = computed(() => {
    const preview = this.preview()
    return preview?.is_geographic === true && preview?.geojson != null
  })

  geojsonData = computed(() => this.preview()?.geojson ?? null)

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  ngOnInit() {
    const linkId = this.route.snapshot.queryParamMap.get('linkId')
    if (linkId) {
      this.integrityLinkId.set(linkId)
      this.selectedTabIndex.set(1)
    }
  }

  constructor() {
    this.renameSubject
      .pipe(debounceTime(400), takeUntilDestroyed())
      .subscribe(({ originalName, newName }) => {
        this.columnConfigs.update((cols) =>
          cols.map((col) =>
            col.original_name === originalName
              ? { ...col, new_name: newName }
              : col
          )
        )
        this.saveConfigAndRefresh()
      })

    // NOTE: any signal read inside an effect body without untracked() creates a
    // subscription that re-triggers the effect. Keep side-effect logic here to
    // deliberately tracked signals (tabIndex, linkId) and wrap any incidental
    // reads in untracked() to prevent unintended re-execution.
    effect(async () => {
      const tabIndex = this.selectedTabIndex()
      const linkId = this.integrityLinkId()

      if (tabIndex === 1 && linkId) {
        // Update URL with linkId parameter
        // eg. /datakern/import?linkId=40e4aa31-022b-484f-bcb8-93423d1c726f
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { linkId },
          queryParamsHandling: 'merge'
        })

        if (!this.metadata() && !this.preview()) {
          const metadata = await this.refreshMetadata(linkId)
          if (metadata) {
            this.columnConfigs.set(metadata.columns)
            this.forceProjection.set(metadata.force_projection ?? null)
          }
          await this.refreshPreview(linkId, false)
        }
      }

      if (tabIndex === 0) {
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { linkId: null },
          queryParamsHandling: 'merge'
        })
      }
    })

    effect(() => {
      if (this.hasExtentError()) {
        this.previewErrorExtent.set(
          this.translate.instant('import.dataSource.error.extent')
        )
      } else {
        this.previewErrorExtent.set(null)
      }
    })
  }

  validFtp(source: SourceData): boolean {
    return (
      !!source.ftpHost &&
      !!source.ftpPort &&
      !!source.ftpPath &&
      !!source.username &&
      !!source.password
    )
  }

  validSource = computed(() => {
    const source = this.importData()?.source
    if (!source) return false

    return (
      (source.type === 'file' && !!source.file) ||
      (source.type === 'url' && !!source.url) ||
      (source.type === 'ftp' && this.validFtp(source))
    )
  })

  onConfigChanged(config: { projection: string; colX: string; colY: string }) {
    this.forceProjection.set({
      type: config.projection || null,
      x_column: config.colX || null,
      y_column: config.colY || null
    })
    this.saveConfigAndRefresh()
  }

  onColumnActionRequested(event: {
    originalName: string
    action: ColumnAction
  }): void {
    const { originalName, action } = event
    if (action === 'remove') {
      this.columnConfigs.update((cols) =>
        cols.map((col) =>
          col.original_name === originalName
            ? { ...col, excluded: !col.excluded }
            : col
        )
      )
      this.saveConfigAndRefresh()
    }
  }

  onColumnRenameRequested(event: {
    originalName: string
    newName: string
  }): void {
    this.renameSubject.next(event)
  }

  onColumnTypeChangeRequested(event: {
    originalName: string
    type: CastType | null
  }): void {
    const { originalName, type } = event
    this.columnConfigs.update((cols) =>
      cols.map((col) =>
        col.original_name === originalName
          ? { ...col, cast_type: type ?? undefined }
          : col
      )
    )
    this.saveConfigAndRefresh()
  }

  onColumnFilterChangeRequested(event: {
    originalName: string
    filter: ColumnFilter | null
  }): void {
    const { originalName, filter } = event
    this.columnConfigs.update((cols) =>
      cols.map((col) =>
        col.original_name === originalName
          ? { ...col, filter: filter ?? undefined }
          : col
      )
    )
    this.saveConfigAndRefresh()
  }

  onSourceChanged(data: SourceData) {
    this.importError.set(null)
    this.importData.update((current) => ({
      ...current,
      source: data
    }))
  }

  cantConfigureDataset() {
    return !this.validSource() || this.importing() || this.polling()
  }

  onColumnNameValidationErrorChanged(event: {
    originalName: string
    error: string | null
  }): void {
    this.columnNameErrors.update((s) => {
      const next = new Set(s)
      if (event.error) {
        next.add(event.originalName)
      } else {
        next.delete(event.originalName)
      }
      return next
    })
  }

  async onConfigureDataset() {
    this.importError.set(null)
    this.importing.set(true)
    this.metadata.update(() => null)
    this.preview.update(() => null)
    this.columnNameErrors.set(new Set())

    try {
      const importResponse = await this.createImportRequest()

      this.integrityLinkId.set(importResponse.integrity_link_id)
      this.dagRunInfo.set({
        dag_id: importResponse.dag_id,
        dag_run_id: importResponse.dag_run_id
      })
      this.integrityLinkId.set(importResponse.integrity_link_id)

      this.importing.set(false)
      this.polling.set(true)

      await this.pollImportStatus(
        importResponse.dag_id,
        importResponse.dag_run_id
      )

      this.selectedTabIndex.set(1)
      this.previewTabIndex.set(0)
    } catch (error) {
      if (error instanceof Error && error.message) {
        this.importError.set(error.message)
      } else if (error instanceof HttpErrorResponse && error.error?.detail) {
        this.importError.set(this.translate.instant(error.error.detail))
      } else {
        this.importError.set(
          this.translate.instant('import.dataSource.unknownError')
        )
      }
    } finally {
      this.importing.set(false)
      this.polling.set(false)
    }
  }

  private async createImportRequest(): Promise<StagingResponse> {
    const source = this.importData().source

    if (source.type === 'file') {
      if (!source.file) {
        throw new Error(this.translate.instant('import.dataSource.missingFile'))
      }

      return await this.api.invoke(submitStagingIngestionStagingPost, {
        body: {
          type: 'file',
          file: source.file
        }
      })
    } else if (source.type === 'url') {
      if (!source.url) {
        throw new Error(this.translate.instant('import.dataSource.missingUrl'))
      }

      return await this.api.invoke(submitStagingIngestionStagingPost, {
        body: {
          type: 'url',
          url: source.url,
          username: source.authEnabled ? source.username.trim() : null,
          password: source.authEnabled ? source.password.trim() : null,
          auth_enabled: source.authEnabled
        }
      })
    } else if (source.type === 'ftp') {
      if (!this.validFtp(source)) {
        throw new Error(this.translate.instant('import.dataSource.missingUrl'))
      }

      return await this.api.invoke(submitStagingIngestionStagingPost, {
        body: {
          type: 'ftp',
          ftp_host: source.ftpHost.trim(),
          ftp_port: source.ftpPort,
          ftp_path: source.ftpPath.trim(),
          username: source.username.trim(),
          password: source.password.trim()
        }
      })
    }

    throw new Error(
      this.translate.instant('import.dataSource.unsupportedSourceType')
    )
  }

  private async pollImportStatus(
    dagId: string,
    dagRunId: string
  ): Promise<void> {
    await lastValueFrom(
      interval(POLL_INTERVAL_MS).pipe(
        switchMap(() =>
          this.api.invoke(
            getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
            {
              dag_id: dagId,
              dag_run_id: dagRunId
            }
          )
        ),
        takeWhile(
          (status: DagRunState) =>
            status === ImportStatus.QUEUED || status === ImportStatus.RUNNING,
          true
        ),
        timeout(MAX_POLL_TIME_MS),
        catchError((error) => {
          if (error.name === 'TimeoutError') {
            return throwError(
              () =>
                new Error(
                  this.translate.instant('import.dataSource.timeoutError')
                )
            )
          }
          return throwError(() => error)
        }),
        switchMap((status: DagRunState) => {
          if (status === ImportStatus.FAILED) {
            const errorMsg = this.translate.instant(
              'import.dataSource.failedError'
            )
            return throwError(() => new Error(errorMsg))
          }
          return of(status)
        })
      )
    )
  }

  private async saveConfigAndRefresh(): Promise<void> {
    const linkId = this.integrityLinkId()
    if (!linkId) return

    this.configSaving.set(true)
    try {
      const updatedMetadata = await this.api.invoke(
        editStagingMetadataIngestionStagingIntegrityLinkIdMetadataPut,
        {
          integrity_link_id: linkId,
          body: {
            columns: this.columnConfigs(),
            title: this.metadata()?.title ?? '',
            file_type: this.metadata()?.file_type ?? null,
            force_projection: this.forceProjection()
          }
        }
      )
      this.metadata.set(updatedMetadata)
      this.columnConfigs.set(updatedMetadata.columns)
    } catch (error) {
      const errorMessage =
        error instanceof HttpErrorResponse
          ? error.error?.detail || error.message
          : 'import.dataSource.unknownError'
      this.previewError.set(
        this.translate.instant(errorMessage) || errorMessage
      )
      return
    } finally {
      this.configSaving.set(false)
    }

    await this.refreshPreview(linkId, false)
  }

  private async refreshMetadata(
    integrityLinkId: string
  ): Promise<StagingMetadataResponse> {
    const metadata = await this.api.invoke(
      getStagingMetadataIngestionStagingIntegrityLinkIdMetadataGet,
      {
        integrity_link_id: integrityLinkId
      }
    )

    this.metadata.set(metadata)

    return metadata
  }

  private async refreshPreview(
    integrityLinkId: string,
    raw: boolean
  ): Promise<void> {
    if (!raw) this.previewLoading.set(true)
    try {
      const preview = await lastValueFrom(
        from(
          this.api.invoke(
            getStagingPreviewIngestionStagingIntegrityLinkIdPreviewGet,
            {
              integrity_link_id: integrityLinkId,
              limit: 10,
              raw,
              include_excluded: true
            }
          )
        ).pipe(timeout(5000))
      )
      this.preview.set(preview)
      if (!raw) this.previewError.set(null)
    } catch (error) {
      if (!raw) {
        const errorMessage =
          error instanceof HttpErrorResponse
            ? error.error?.detail || error.message
            : 'import.dataSource.unknownError'
        this.previewError.set(this.translate.instant(errorMessage))
        this.previewTabIndex.set(0)
        await this.refreshPreview(integrityLinkId, true)
      }
    } finally {
      if (!raw) this.previewLoading.set(false)
    }
  }

  onTitleChanged(title: string) {
    this.metadata.update((m) => (m ? { ...m, title } : m))
  }

  async onValidateDataset(title: string) {
    this.validationError.set(null)
    this.processing.set(true)

    try {
      await this.api.invoke(processStagingDataIngestionProcessPost, {
        body: {
          integrity_link_id: this.integrityLinkId()!,
          title: title
        }
      })

      this.processing.set(false)
      this.router.navigate([this.integrityLinkId(), 'edit'])
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.error?.detail) {
        this.validationError.set(error.error.detail)
      } else {
        this.validationError.set(
          this.translate.instant('import.dataSource.validationError')
        )
      }
      this.processing.set(false)
    }
  }
}
