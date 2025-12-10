import { Component, OnInit } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { CommonModule } from '@angular/common'
import {
  EventsListComponent,
  Event
} from '../../shared/components/events-list/events-list.component'

@Component({
  selector: 'app-events',
  imports: [CommonModule, EventsListComponent],
  templateUrl: './events.component.html',
  styleUrl: './events.component.css'
})
export class EventsComponent implements OnInit {
  reference: string | null = null
  events: Event[] = []

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.reference = this.route.snapshot.paramMap.get('reference')
    // TODO: Fetch events from API based on reference
    // For now, using mock data
    this.loadMockEvents()
  }

  private loadMockEvents(): void {
    this.events = [
      {
        id: '1',
        timestamp: new Date().toISOString(),
        type: 'Run manual',
        message: 'Data import process has been initiated',
        status: 'info'
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 60000).toISOString(),
        type: 'Programmé',
        message: 'Data validation completed successfully',
        status: 'success'
      },
      {
        id: '3',
        timestamp: new Date(Date.now() - 120000).toISOString(),
        type: 'Run manual',
        message: 'Processing 1000 records',
        status: 'info'
      },
      {
        id: '4',
        timestamp: new Date(Date.now() - 180000).toISOString(),
        type: 'Programmé',
        message:
          'Failed to process record: Invalid data format in column "email"',
        status: 'error'
      },
      {
        id: '5',
        timestamp: new Date(Date.now() - 30000).toISOString(),
        type: 'Run manual',
        message: 'Currently processing batch 2 of 10',
        status: 'working'
      }
    ]
  }
}
