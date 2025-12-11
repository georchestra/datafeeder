import { Component, Input } from '@angular/core'
import { CommonModule } from '@angular/common'

export type StatusType = 'success' | 'error' | 'warning' | 'info' | 'running'

@Component({
  selector: 'app-status-badge',
  imports: [CommonModule],
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.css'
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: StatusType
}
