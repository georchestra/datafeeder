import { Component, Input, Output, EventEmitter } from '@angular/core'
import { CommonModule } from '@angular/common'
import { EventComponent } from '../event/event.component'
import type { Event } from '../event/event.component'

export type { Event }

@Component({
  selector: 'app-events-list',
  imports: [CommonModule, EventComponent],
  templateUrl: './events-list.component.html',
  styleUrl: './events-list.component.css'
})
export class EventsListComponent {
  @Input({ required: true }) events: Event[] = []
  @Input({ required: true }) reference!: string
  @Output() downloadLogsClicked = new EventEmitter<{
    dag_id: string
    dag_run_id: string
  }>()
}
