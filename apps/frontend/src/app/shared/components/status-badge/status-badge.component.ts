import { Component, Input } from '@angular/core'
import { CommonModule } from '@angular/common'
import { StatusType } from '../../types/status-type'
import { TranslateDirective } from '@ngx-translate/core'

@Component({
  selector: 'app-status-badge',
  imports: [CommonModule, TranslateDirective],
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.css'
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: StatusType
}
