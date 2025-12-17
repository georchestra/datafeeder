import { Component, OnInit, inject, signal } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { CommonModule } from '@angular/common'
import {
  EventsListComponent,
  Event
} from '../../shared/components/events-list/events-list.component'
import { Api } from '../../core/api/api'
import { getDagRunsAirflowDagsDagIdRunsGet } from '../../core/api/fn/airflow/get-dag-runs-airflow-dags-dag-id-runs-get'
import { getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet } from '../../core/api/fn/airflow/get-dag-run-logs-airflow-dags-dag-id-runs-dag-run-id-logs-get'
import { DagRunCollectionResponse } from '../../core/api/models/dag-run-collection-response'

import { downloadTextBlob } from '../../shared/utils/download.util'
import { EventTypeType } from '../../shared/components/event-type-badge/event-type-badge.component'
import { DagRunResponse } from '../../core/api/models/dag-run-response'
import { DagRunState } from '../../core/api/models'

const DAG_RUNGS_PAGE_SIZE = 20

@Component({
  selector: 'app-events',
  imports: [CommonModule, EventsListComponent],
  templateUrl: './events.component.html',
  styleUrl: './events.component.css'
})
export class EventsComponent implements OnInit {
  private route = inject(ActivatedRoute)
  private api = inject(Api)

  reference: string | null = null
  events = signal<Event[]>([])

  ngOnInit(): void {
    this.reference = this.route.snapshot.paramMap.get('reference')
    if (this.reference) {
      this.loadDagRuns(this.reference)
    }
  }

  private async loadDagRuns(dagId: string): Promise<void> {
    try {
      const response: DagRunCollectionResponse = await this.api.invoke(
        getDagRunsAirflowDagsDagIdRunsGet,
        {
          dag_id: dagId,
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

  private mapRunTypeToEventType(runType: string): EventTypeType {
    return runType === 'manual' ? 'Run manual' : 'Programmé'
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
    try {
      const logs = await this.api.invoke(
        getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet,
        { dag_id, dag_run_id }
      )
      downloadTextBlob(logs, `logs_${dag_id}_${dag_run_id}.txt`)
    } catch (error) {
      console.error('Failed to fetch event logs:', error)
    }
  }
}
