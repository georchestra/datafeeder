import { HttpClient } from '@angular/common/http'
import { Component, effect, inject, signal } from '@angular/core'
import { MatTabsModule } from '@angular/material/tabs'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig,
} from '@ng-icons/core'
import {
  iconoirNumber1Square,
  iconoirNumber2Square,
} from '@ng-icons/iconoir'
import { ButtonComponent } from 'geonetwork-ui'
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
  getDagRunStatusAirflowDagsDagIdRunsDagRunIdStatusGet,
  submitStagingIngestionStagingPost
} from '../../../core/api/functions'
import type { DagRunState, StagingResponse } from '../../../core/api/models'
import type { SourceData } from '../data-source-selector/data-source-selector.component'
import { DataSourceSelectorComponent } from '../data-source-selector/data-source-selector.component'
import { DatasetConfigurationComponent } from '../dataset-configuration/dataset-configuration.component'

const POLL_INTERVAL_MS = 500
const MAX_POLL_TIME_MS = 30000

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
    DataSourceSelectorComponent,
    DatasetConfigurationComponent
  ],
  templateUrl: './data-import-wizard.component.html',
  styleUrls: ['./data-import-wizard.component.scss'],
  providers: [
    provideIcons({
      iconoirNumber1Square,
      iconoirNumber2Square
    }),
    provideNgIconsConfig({
      size: '2em',
    }),
  ]
})
export class DataImportWizardComponent {
  private http = inject(HttpClient)
  private api = inject(Api)

  selectedTabIndex = signal(0)
  importData = signal<ImportWizardData>({
    source: { type: 'url', url: '' }
  })

  validSource = signal(false)
  validating = signal(false)
  importing = signal(false)
  polling = signal(false)
  importError = signal<string | null>(null)
  dagRunInfo = signal<{ dag_id: string; dag_run_id: string } | null>(null)

  constructor() {
    effect((onCleanup) => {
      const url = this.importData().source.url

      // Basic format validation
      if (!url || !/^https?:\/\/.+/.test(url)) {
        this.validSource.set(false)
        this.validating.set(false)
        return
      }

      // Start validation
      this.validating.set(true)

      const subscription = of(url) // TODO proxify request to avoid CORS issues
        .pipe(
          debounceTime(300),
          tap(() => this.validating.set(true)),
          switchMap((url) =>
            this.http
              .head(url, { observe: 'response' })
              .pipe(catchError(() => of(null)))
          ),
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
  }

  onSourceChanged(data: SourceData) {
    this.importData.update((current) => ({
      ...current,
      source: data
    }))
  }

  cantConfigureDataset() {
    return !this.validSource() || this.validating() || this.importing() || this.polling()
  }

  async onConfigureDataset() {
    this.importError.set(null)
    this.importing.set(true)

    try {
      const importResponse = await this.createImportRequest()

      this.dagRunInfo.set({
        dag_id: importResponse.dag_id,
        dag_run_id: importResponse.dag_run_id
      })

      this.importing.set(false)
      this.polling.set(true)

      await this.pollImportStatus(
        importResponse.dag_id,
        importResponse.dag_run_id
      )

      this.selectedTabIndex.set(1)
    } catch (error) {
      this.importError.set(
        error instanceof Error ? error.message : 'Une erreur est survenue'
      )
    } finally {
      this.importing.set(false)
      this.polling.set(false)
    }
  }

  private async createImportRequest(): Promise<StagingResponse> {
    const url = this.importData().source.url

    if (!url) {
      throw new Error('URL manquante')
    }

    return await this.api.invoke(submitStagingIngestionStagingPost, {
      body: {
        type: 'url',
        url: url
      }
    })
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
            return throwError(() => new Error("Délai d'attente dépassé"))
          }
          return throwError(() => error)
        }),
        switchMap((status: DagRunState) => {
          if (status === ImportStatus.FAILED) {
            const errorMsg = 'Le traitement a échoué'
            return throwError(() => new Error(errorMsg))
          }
          return of(status)
        })
      )
    )
  }
}
