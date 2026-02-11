import { CommonModule } from '@angular/common'
import { Component, OnInit, inject, signal } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import { getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet } from '../../core/api/fn/airflow/get-dag-run-logs-airflow-dags-dag-id-runs-dag-run-id-logs-get'
import { DagRunState, IntegrityLinkResponse } from '../../core/api/models'
import { DagRunCollectionResponse } from '../../core/api/models/dag-run-collection-response'
import { DagRunResponse } from '../../core/api/models/dag-run-response'
import { EventType } from '../../shared/components/event-type-badge/event-type-badge.component'
import {
  Event,
  EventsListComponent
} from '../../shared/components/events-list/events-list.component'
import { downloadTextBlob } from '../../shared/utils/download.util'
import {
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
  getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet
} from '../../core/api/functions'

const DAG_RUNGS_PAGE_SIZE = 20

@Component({
  selector: 'app-events',
  imports: [CommonModule, EventsListComponent, TranslatePipe],
  templateUrl: './events.component.html',
  styleUrl: './events.component.css'
})
export class EventsComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)

  intlink_id: string | null = null
  events = signal<Event[]>([])
  downloadingEventId = signal<string | null>(null)
  integrity_link = signal<IntegrityLinkResponse | null>(null)

  ngOnInit(): void {
    this.intlink_id =
      this.route.parent?.snapshot.paramMap.get('intlink_id') ?? null
    if (this.intlink_id) {
      this.loadDagRuns(this.intlink_id)
      this.loadIntegrityLink(this.intlink_id)
    }
  }

  private async loadDagRuns(intlinkId: string): Promise<void> {
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
            if (!a.start_date && b.start_date) return -1
            if (a.start_date && !b.start_date) return 1
            return 0
          })
      )
    } catch (error) {
      console.error('Error loading DAG runs:', error)
    }
  }

  private transformDagRunToEvent(dagRun: DagRunResponse): Event {
    return {
      id: dagRun.dag_run_id,
      start_date: dagRun.start_date || null,
      end_date: dagRun.end_date || null,
      duration: dagRun.duration || null,
      type: this.mapRunTypeToEventType(dagRun.run_type),
      status: this.mapDagStateToEventStatus(dagRun.state)
    }
  }

  private mapRunTypeToEventType(runType: string): EventType {
    return runType === 'manual' ? 'manual' : 'scheduled'
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
    this.downloadingEventId.set(dag_run_id)
    try {
      const logs = await this.api.invoke(
        getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet,
        { dag_id: 'process_dag', dag_run_id: dag_run_id }
      )
      downloadTextBlob(logs, `logs_${dag_id}_${dag_run_id}.txt`)
      this.downloadingEventId.set(null)
    } catch (error) {
      console.error('Failed to fetch event logs:', error)
    }
  }

  private async loadIntegrityLink(integrityLinkId: string): Promise<void> {
    const metadata = await this.api.invoke(
      getIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdGet,
      {
        integrity_link_id: integrityLinkId
      }
    )
    this.integrity_link.update(() => metadata)
  }
}
