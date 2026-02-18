import { CommonModule } from '@angular/common'
import { Component, EventEmitter, Input, Output, OnInit, DestroyRef, inject } from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { interval } from 'rxjs'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import type { Event } from '../event/event.component'
import { EventComponent } from '../event/event.component'

export type { Event }

@Component({
  selector: 'app-events-list',
  imports: [CommonModule, EventComponent, TranslatePipe],
  templateUrl: './events-list.component.html',
  styleUrl: './events-list.component.css'
})
export class EventsListComponent implements OnInit {
  @Input({ required: true }) events: Event[] = []
  @Input({ required: true }) reference!: string
  @Input() downloadingEventId: string | null = null
  @Output() downloadLogsClicked = new EventEmitter<{
    dag_id: string
    dag_run_id: string
  }>()
  @Output() refreshRequested = new EventEmitter<void>()

  private destroyRef = inject(DestroyRef)

  ngOnInit(): void {
    // Emit refresh event every 2 seconds
    interval(2000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.refreshRequested.emit()
      })
  }
}
