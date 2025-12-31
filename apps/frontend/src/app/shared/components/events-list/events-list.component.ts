import { CommonModule } from '@angular/common'
import { Component, EventEmitter, Input, Output } from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import type { Event } from '../event/event.component'
import { EventComponent } from '../event/event.component'

export type { Event }

@Component({
  selector: 'app-events-list',
  imports: [CommonModule, EventComponent, TranslatePipe],
  templateUrl: './events-list.component.html',
  styleUrl: './events-list.component.css'
})
export class EventsListComponent {
  @Input({ required: true }) events: Event[] = []
  @Input({ required: true }) reference!: string
  @Input() downloadingEventId: string | null = null
  @Output() downloadLogsClicked = new EventEmitter<{
    dag_id: string
    dag_run_id: string
  }>()
}
