import { CommonModule } from '@angular/common'
import { Component, OnInit, inject, signal } from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import { getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet } from '../../core/api/fn/airflow/get-dag-run-logs-airflow-dags-dag-id-runs-dag-run-id-logs-get'
import { DagRunState } from '../../core/api/models'
import { DagRunCollectionResponse } from '../../core/api/models/dag-run-collection-response'
import { DagRunResponse } from '../../core/api/models/dag-run-response'
import { IntegrityLinkStore } from '../../layout/integrity-link.store'
import { EventType } from '../../shared/components/event-type-badge/event-type-badge.component'
import {
  Event,
  EventsListComponent
} from '../../shared/components/events-list/events-list.component'
import { UiAlertBoxComponent } from '../../shared/components/ui-alert-box/ui-alert-box.component'
import { downloadTextBlob } from '../../shared/utils/download.util'
import { getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet } from '../../core/api/functions'

const DAG_RUNGS_PAGE_SIZE = 20

@Component({
  selector: 'app-events',
  imports: [
    CommonModule,
    EventsListComponent,
    UiAlertBoxComponent,
    TranslatePipe
  ],
  templateUrl: './events.component.html',
  styleUrl: './events.component.css'
})
export class EventsComponent implements OnInit {
  private api = inject(Api)
  readonly store = inject(IntegrityLinkStore)

  intlink_id = this.store.intlinkId()
  events = signal<Event[]>([])
  downloadingEventId = signal<string | null>(null)
  loadError = signal<string | null>(null)
  downloadError = signal<string | null>(null)

  ngOnInit(): void {
    if (this.intlink_id) {
      this.loadDagRuns(this.intlink_id)
    }
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
