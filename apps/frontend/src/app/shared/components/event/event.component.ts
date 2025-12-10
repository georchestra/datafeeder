import { Component, Input } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatIconModule } from '@angular/material/icon'
import { StatusBadgeComponent } from '../status-badge/status-badge.component'
import {
  EventTypeBadgeComponent,
  EventTypeType
} from '../event-type-badge/event-type-badge.component'

export interface Event {
  id: string
  timestamp: string
  type: EventTypeType
  message: string
  status: 'success' | 'error' | 'warning' | 'info' | 'working'
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
}
