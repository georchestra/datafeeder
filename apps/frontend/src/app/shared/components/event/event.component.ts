import { Component, Input, Output, EventEmitter } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatIconModule } from '@angular/material/icon'
import { StatusBadgeComponent } from '../status-badge/status-badge.component'
import {
  EventTypeBadgeComponent,
  EventTypeType
} from '../event-type-badge/event-type-badge.component'
import { StatusType } from '../../types/status-type'

export interface Event {
  id: string
  start_date: string | null
  end_date: string | null
  duration: number | null
  type: EventTypeType
  status: StatusType
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
  @Input({ required: false }) downloading: boolean = false

  formatDuration(duration: number | null): string | undefined {
    if (!duration) return undefined
    const date = new Date(duration * 1000) // Convert seconds to milliseconds
    return date.toISOString().slice(11, 23) // Extract HH:mm:ss.SSS
  }

  @Output() downloadLogsClicked = new EventEmitter<{
    dag_id: string
    dag_run_id: string
  }>()

  downloadLogs() {
    if (this.downloading) return
    this.downloadLogsClicked.emit({
      dag_id: this.reference,
      dag_run_id: this.event.id
    })
  }
}
