import { Component, Input } from '@angular/core'
import { CommonModule } from '@angular/common'
import { EventComponent, Event } from '../event/event.component'

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
}
