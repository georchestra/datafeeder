import { Component, Input } from '@angular/core'
import { CommonModule } from '@angular/common'

export type EventType = 'manual' | 'scheduled'

@Component({
  selector: 'app-event-type-badge',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './event-type-badge.component.html',
  styleUrl: './event-type-badge.component.css'
})
export class EventTypeBadgeComponent {
  @Input() type!: EventType
}
