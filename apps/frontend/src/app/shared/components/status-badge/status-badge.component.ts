import { Component, Input } from '@angular/core'
import { CommonModule } from '@angular/common'
import { StatusType } from '../../types/status-type'

@Component({
  selector: 'app-status-badge',
  imports: [CommonModule],
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.css'
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: StatusType
}
