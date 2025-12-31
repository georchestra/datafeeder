import { CommonModule } from '@angular/common'
import { Component, Input } from '@angular/core'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { TranslateDirective } from '@ngx-translate/core'

export type EventType = 'manual' | 'scheduled'
marker('event.type.manual')
marker('event.type.scheduled')

@Component({
  selector: 'app-event-type-badge',
  standalone: true,
  imports: [CommonModule, TranslateDirective],
  templateUrl: './event-type-badge.component.html',
  styleUrl: './event-type-badge.component.css'
})
export class EventTypeBadgeComponent {
  @Input() type!: EventType
}
