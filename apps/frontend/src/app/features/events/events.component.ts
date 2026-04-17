import { CommonModule } from '@angular/common'
import {
  Component,
  OnInit,
  effect,
  inject,
  signal,
  untracked
} from '@angular/core'
import { RecurrencePreset } from '../../core/api/models/recurrence-preset'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import { getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet } from '../../core/api/fn/airflow/get-dag-run-logs-airflow-dags-dag-id-runs-dag-run-id-logs-get'
import { DagRunState, RecurrencePresetItem } from '../../core/api/models'
import { DagRunCollectionResponse } from '../../core/api/models/dag-run-collection-response'
import { DagRunResponse } from '../../core/api/models/dag-run-response'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { ErrorToastStore } from '../../core/stores/error-toast.store'
import { EventType } from '../../shared/components/event-type-badge/event-type-badge.component'
import {
  Event,
  EventsListComponent
} from '../../shared/components/events-list/events-list.component'
import { UiAlertBoxComponent } from '../../shared/components/ui-alert-box/ui-alert-box.component'
import { RecurrenceSelectorComponent } from '../../shared/components/recurrence-selector/recurrence-selector.component'
import { downloadTextBlob } from '../../shared/utils/download.util'
import {
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
  listRecurrencePresetsIngestionRecurrencePresetsGet,
  updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch
} from '../../core/api/functions'

const DAG_RUNGS_PAGE_SIZE = 20

@Component({
  selector: 'app-events',
  imports: [
    CommonModule,
    EventsListComponent,
    UiAlertBoxComponent,
    RecurrenceSelectorComponent,
    TranslatePipe
  ],
  templateUrl: './events.component.html',
  styleUrl: './events.component.css'
})
export class EventsComponent implements OnInit {
  private api = inject(Api)
  readonly store = inject(IntegrityLinkStore)
  private errorToastStore = inject(ErrorToastStore)

  intlink_id = this.store.intlinkId()
  events = signal<Event[]>([])
  recurrencePresets = signal<RecurrencePresetItem[]>([])
  readonly selectedPresetId: ReturnType<typeof signal<RecurrencePreset | null>>
  downloadingEventId = signal<string | null>(null)
  loadError = signal<string | null>(null)
  downloadError = signal<string | null>(null)

  constructor() {
    const link = this.store.integrityLink()
    this.selectedPresetId = signal<RecurrencePreset | null>(
      link?.schedule_enabled ? link.preset_id ?? null : null
    )

    let initialized = false
    effect(() => {
      const presetId = this.selectedPresetId()
      if (!initialized) {
        initialized = true
        return
      }
      const intlinkId = untracked(() => this.intlink_id)
      if (!intlinkId) return
      this.api
        .invoke(
          updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
          {
            integrity_link_id: intlinkId,
            body: { preset: presetId }
          }
        )
        .then((updatedLink) => {
          this.store.integrityLink.update((current) => ({
            ...current!,
            preset_id: updatedLink.preset_id,
            schedule: updatedLink.schedule,
            schedule_enabled: updatedLink.schedule_enabled
          }))
        })
        .catch((err) => {
          console.error('Failed to update schedule:', err)
          this.errorToastStore.add('updateSchedule')
        })
    })
  }

  ngOnInit(): void {
    if (this.intlink_id) {
      this.loadDagRuns(this.intlink_id)
    }

    this.api
      .invoke(listRecurrencePresetsIngestionRecurrencePresetsGet, {})
      .then((presets) => this.recurrencePresets.set(presets))
      .catch((err) => {
        console.error('Failed to load recurrence presets:', err)
        this.errorToastStore.add('loadPresets')
      })
  }

  private async loadDagRuns(intlinkId: string): Promise<void> {
    this.loadError.set(null)
    try {
      const response: DagRunCollectionResponse = await this.api.invoke(
        getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
        {
          dag_id: 'process_dag',
          intlink_id: intlinkId,
          limit: DAG_RUNGS_PAGE_SIZE
        }
      )

      this.events.set(
        response.dag_runs
          .map((dagRun) => this.transformDagRunToEvent(dagRun))
          .sort((a, b) => {
            // Events without start_date come first
            if (!a.start_date && b.start_date) return -1
            if (a.start_date && !b.start_date) return 1

            // Both have dates - sort by date (most recent first)
            if (a.start_date && b.start_date) {
              return (
                new Date(b.start_date).getTime() -
                new Date(a.start_date).getTime()
              )
            }

            return 0
          })
      )
    } catch (error) {
      console.error('Error loading DAG runs:', error)
      this.loadError.set('events.error.load')
    }
  }

  private transformDagRunToEvent(dagRun: DagRunResponse): Event {
    return {
      id: dagRun.dag_run_id,
      start_date: dagRun.start_date || null,
      end_date: dagRun.end_date || null,
      duration: dagRun.duration || null,
      type: this.mapRunTypeToEventType(dagRun.dag_run_id),
      status: this.mapDagStateToEventStatus(dagRun.state)
    }
  }

  private mapRunTypeToEventType(runType: string): EventType {
    return runType.includes('_manual') ? 'manual' : 'scheduled'
  }

  private mapDagStateToEventStatus(
    state: DagRunState
  ): 'success' | 'error' | 'warning' | 'running' | 'queued' {
    if (state === 'failed') {
      return 'error'
    }
    return state
  }

  async onDownloadLogsClicked({
    dag_id,
    dag_run_id
  }: {
    dag_id: string
    dag_run_id: string
  }) {
    this.downloadError.set(null)
    this.downloadingEventId.set(dag_run_id)
    try {
      const logs = await this.api.invoke(
        getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet,
        { dag_id: 'process_dag', dag_run_id: dag_run_id }
      )
      downloadTextBlob(logs, `logs_${dag_id}_${dag_run_id}.txt`)
    } catch (error) {
      console.error('Failed to fetch event logs:', error)
      this.downloadError.set('events.error.downloadLogs')
    } finally {
      this.downloadingEventId.set(null)
    }
  }

  onRefreshRequested(): void {
    if (this.intlink_id) {
      this.loadDagRuns(this.intlink_id)
    }
  }
}
