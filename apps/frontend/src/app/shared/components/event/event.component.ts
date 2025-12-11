import { Component, Input, Output, EventEmitter } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatIconModule } from '@angular/material/icon'
import { StatusBadgeComponent } from '../status-badge/status-badge.component'
import {
  EventTypeBadgeComponent,
  EventTypeType
} from '../event-type-badge/event-type-badge.component'

export interface Event {
  id: string
  start_date: string | null
  end_date: string | null
  duration: number | null
  type: EventTypeType
  status: 'success' | 'error' | 'warning' | 'info' | 'running'
}

@Component({
  selector: 'app-event',
  imports: [
    CommonModule,
    MatIconModule,
    StatusBadgeComponent,
    EventTypeBadgeComponent
  ],
  templateUrl: './event.component.html',
  styleUrl: './event.component.css'
})
export class EventComponent {
  @Input({ required: true }) event!: Event
  @Input({ required: true }) reference!: string

  formatDuration(duration: number | null): string {
    if (!duration) return '00:00:00.000'
    const hours = Math.floor(duration / 3600)
    const minutes = Math.floor((duration % 3600) / 60)
    const seconds = Math.floor(duration % 60)
    const milliseconds = Math.floor((duration % 1) * 1000)
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(
      2,
      '0'
    )}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(
      3,
      '0'
    )}`
  }

  @Output() downloadLogsClicked = new EventEmitter<{
    dag_id: string
    dag_run_id: string
  }>()

  downloadLogs() {
    this.downloadLogsClicked.emit({
      dag_id: this.reference,
      dag_run_id: this.event.id
    })
  }
}
