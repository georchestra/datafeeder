import { CommonModule } from '@angular/common'
import { Component, EventEmitter, Input, Output } from '@angular/core'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirDownload } from '@ng-icons/iconoir'
import { matAutorenewOutline } from '@ng-icons/material-icons/outline'
import { TranslatePipe } from '@ngx-translate/core'
import { StatusType } from '../../types/status-type'
import {
  EventTypeBadgeComponent,
  EventType
} from '../event-type-badge/event-type-badge.component'
import { StatusBadgeComponent } from '../status-badge/status-badge.component'

export interface Event {
  id: string
  start_date: string | null
  end_date: string | null
  duration: number | null
  type: EventType
  status: StatusType
}

@Component({
  selector: 'app-event',
  imports: [
    CommonModule,
    NgIconComponent,
    StatusBadgeComponent,
    EventTypeBadgeComponent,
    TranslatePipe
  ],
  templateUrl: './event.component.html',
  styleUrl: './event.component.css',
  providers: [
    provideIcons({
      iconoirDownload,
      matAutorenewOutline
    }),
    provideNgIconsConfig({
      size: '1.5em'
    })
  ]
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
