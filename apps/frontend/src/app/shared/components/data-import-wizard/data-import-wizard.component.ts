import { HttpClient } from '@angular/common/http'
import { Component, effect, inject, signal } from '@angular/core'
import { MatTabsModule } from '@angular/material/tabs'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirNumber1Square, iconoirNumber2Square } from '@ng-icons/iconoir'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { ButtonComponent, SpinningLoaderComponent } from 'geonetwork-ui'
import { Router } from '@angular/router'
import {
  catchError,
  debounceTime,
  interval,
  lastValueFrom,
  of,
  switchMap,
  takeWhile,
  tap,
  throwError,
  timeout
} from 'rxjs'
import { Api } from '../../../core/api/api'
import {
  getStagingMetadataIngestionStagingIntegrityLinkIdMetadataGet,
  getStagingPreviewIngestionStagingIntegrityLinkIdPreviewGet,
  getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
  submitStagingIngestionStagingPost,
  processStagingDataIngestionProcessPost
} from '../../../core/api/functions'
import type {
  DagRunState,
  StagingResponse,
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import type { SourceData } from '../data-source-selector/data-source-selector.component'
import { DataSourceSelectorComponent } from '../data-source-selector/data-source-selector.component'
import { DatasetConfigurationComponent } from '../dataset-configuration/dataset-configuration.component'
import { DatasetPreviewTableComponent } from '../dataset-preview-table/dataset-preview-table.component'

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
    MatTabsModule,
    NgIconComponent,
    ButtonComponent,
    SpinningLoaderComponent,
    DataSourceSelectorComponent,
    DatasetConfigurationComponent,
    TranslatePipe,
    DatasetPreviewTableComponent
  ],
  templateUrl: './data-import-wizard.component.html',
  styleUrls: ['./data-import-wizard.component.scss'],
  providers: [
    provideIcons({
      iconoirNumber1Square,
      iconoirNumber2Square
    }),
    provideNgIconsConfig({
      size: '2em'
    })
  ]
})
export class DataImportWizardComponent {
  private http = inject(HttpClient)
  private api = inject(Api)
  private translate = inject(TranslateService)
  private router = inject(Router)

  selectedTabIndex = signal(0)
  importData = signal<ImportWizardData>({
    source: {
      type: 'url',
      url: '',
      authEnabled: false,
      username: '',
      password: ''
    }
  })

  validSource = signal(false)
  validating = signal(false)
  importing = signal(false)
  polling = signal(false)
  importError = signal<string | null>(null)
  metadata = signal<StagingMetadataResponse | null>(null)
  preview = signal<StagingPreviewResponse | null>(null)
  dagRunInfo = signal<{ dag_id: string; dag_run_id: string } | null>(null)
  integrityLinkId = signal<string | null>(null)
  processing = signal(false)
  validationError = signal<string | null>(null)

  constructor() {
    effect((onCleanup) => {
      const source = this.importData().source

      // Basic format validation
      if (!source.url || !/^https?:\/\/.+/.test(source.url)) {
        this.validSource.set(false)
        this.validating.set(false)
        return
      }

      // Start validation
      this.validating.set(true)

      const subscription = of(source.url) // TODO proxify request to avoid CORS issues
        .pipe(
          debounceTime(300),
          tap(() => this.validating.set(true)),
          switchMap((url) => {
            const options: any = { observe: 'response', responseType: 'text' }

            if (source.authEnabled && source.username && source.password) {
              options.withCredentials = true

              const urlObj = new URL(url)
              urlObj.username = source.username
              urlObj.password = source.password
              url = urlObj.toString()
            }

            return this.http
              .head(url, options)
              .pipe(catchError(() => of({ status: 0 } as any)))
          }),
          tap(() => this.validating.set(false))
        )
        .subscribe((response) => {
          this.validSource.set(response?.status === 200)
        })

      onCleanup(() => {
        subscription.unsubscribe()
        this.validating.set(false)
      })
    })

    // Fetch staging data when tab 2 is selected and integrityLinkId is available
    effect(() => {
      const tabIndex = this.selectedTabIndex()
      const linkId = this.integrityLinkId()

      if (tabIndex === 1 && linkId && !this.metadata() && !this.preview()) {
        this.fetchStagingData(linkId)
      }
    })
  }

  onSourceChanged(data: SourceData) {
    this.importData.update((current) => ({
      ...current,
      source: data
    }))
  }

  cantConfigureDataset() {
    return (
      !this.validSource() ||
      this.validating() ||
      this.importing() ||
      this.polling()
    )
  }

  async onConfigureDataset() {
    this.importError.set(null)
    this.importing.set(true)

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
    } catch (error) {
      this.importError.set(
        error instanceof Error
          ? error.message
          : this.translate.instant('import.dataSource.unknownError')
      )
    } finally {
      this.importing.set(false)
      this.polling.set(false)
    }
  }

  private async createImportRequest(): Promise<StagingResponse> {
    const source = this.importData().source

    if (source.type === 'url') {
      if (!source.url) {
        throw new Error(this.translate.instant('import.dataSource.missingUrl'))
      }

      return await this.api.invoke(submitStagingIngestionStagingPost, {
        body: {
          type: 'url',
          url: source.url,
          username: source.authEnabled ? source.username : null,
          password: source.authEnabled ? source.password : null,
          auth_enabled: source.authEnabled
        }
      })
    } else if (source.type === 'file') {
      // TODO: implement file upload handling
      throw new Error(
        this.translate.instant('import.dataSource.fileImportNotImplemented')
      )
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

  private async fetchStagingData(integrityLinkId: string): Promise<void> {
    try {
      const [metadata, preview] = await Promise.all([
        this.api.invoke(
          getStagingMetadataIngestionStagingIntegrityLinkIdMetadataGet,
          {
            integrity_link_id: integrityLinkId
          }
        ),
        this.api.invoke(
          getStagingPreviewIngestionStagingIntegrityLinkIdPreviewGet,
          {
            integrity_link_id: integrityLinkId,
            limit: 10
          }
        )
      ])

      this.metadata.set(metadata)
      this.preview.set(preview)
    } catch (error) {
      console.error('Error fetching staging data:', error)
    }
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
      // the route should be able to target with a tag with dag_run_id
      this.router.navigate(['/events', 'process_dag'])
    } catch (error) {
      this.validationError.set(
        error instanceof Error
          ? error.message
          : this.translate.instant('import.dataSource.validationError')
      )
      this.processing.set(false)
    }
  }
}
