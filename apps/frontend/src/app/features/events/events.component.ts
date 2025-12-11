import { Component, OnInit, inject, signal } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { CommonModule } from '@angular/common'
import {
  EventsListComponent,
  Event
} from '../../shared/components/events-list/events-list.component'
import { Api } from '../../core/api/api'
import { getDagRunsAirflowDagsDagIdRunsGet } from '../../core/api/fn/airflow/get-dag-runs-airflow-dags-dag-id-runs-get'
import { DagRunCollectionResponse } from '../../core/api/models/dag-run-collection-response'
import { DagRunResponse } from '../../core/api/models/dag-run-response'
import { EventTypeType } from '../../shared/components/event-type-badge/event-type-badge.component'

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
          limit: 20
        }
      )

      this.events.set(
        response.dag_runs.map((dagRun) => this.transformDagRunToEvent(dagRun))
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
    state: string
  ): 'success' | 'error' | 'warning' | 'info' | 'running' {
    switch (state) {
      case 'success':
        return 'success'
      case 'failed':
        return 'error'
      case 'running':
        return 'running'
      case 'queued':
        return 'info'
      default:
        return 'info'
    }
  }

  async onDownloadLogsClicked({
    dag_id,
    dag_run_id
  }: {
    dag_id: string
    dag_run_id: string
  }) {
    const { getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet } = await import(
      '../../core/api/fn/airflow/get-dag-run-logs-airflow-dags-dag-id-runs-dag-run-id-logs-get'
    )
    try {
      const logs = await this.api.invoke(
        getDagRunLogsAirflowDagsDagIdRunsDagRunIdLogsGet,
        { dag_id, dag_run_id }
      )
      console.log('Event logs:', logs)
      // TODO: Format and trigger download as file if needed
    } catch (error) {
      console.error('Failed to fetch event logs:', error)
    }
  }
}
