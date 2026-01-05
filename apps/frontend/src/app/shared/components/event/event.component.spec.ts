import { ComponentFixture, TestBed } from '@angular/core/testing'
import { By } from '@angular/platform-browser'
import { MatIconModule } from '@angular/material/icon'
import { CommonModule } from '@angular/common'
import { EventComponent, Event } from './event.component'
import { StatusBadgeComponent } from '../status-badge/status-badge.component'
import { EventTypeBadgeComponent } from '../event-type-badge/event-type-badge.component'

describe('EventComponent', () => {
  let fixture: ComponentFixture<EventComponent>
  let component: EventComponent
  const event: Event = {
    id: 'run-123',
    start_date: '2024-01-01T10:00:00Z',
    end_date: '2024-01-01T10:10:00Z',
    duration: 600,
    type: 'Run manuel',
    status: 'error'
  }
  const reference = 'DAG-REF-1'

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        EventComponent,
        StatusBadgeComponent,
        EventTypeBadgeComponent,
        MatIconModule,
        CommonModule
      ]
    }).compileComponents()
    fixture = TestBed.createComponent(EventComponent)
    component = fixture.componentInstance
    component.event = event
    component.reference = reference
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  it('should render reference and event info', () => {
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain(reference)
    expect(compiled.textContent).toContain('Début')
    expect(compiled.textContent).toContain('Fin')
    expect(compiled.textContent).toContain('Durée')
    expect(compiled.textContent).toContain('Run manuel')
  })

  it('should emit downloadLogsClicked when button is clicked', () => {
    vi.spyOn(component.downloadLogsClicked, 'emit')
    // Only visible if status is 'error'
    const button = fixture.debugElement.query(By.css('button'))
    expect(button).toBeTruthy()
    button.nativeElement.click()
    expect(component.downloadLogsClicked.emit).toHaveBeenCalledWith({
      dag_id: reference,
      dag_run_id: event.id
    })
  })
})
