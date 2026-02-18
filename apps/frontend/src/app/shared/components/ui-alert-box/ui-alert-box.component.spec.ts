import { ComponentFixture, TestBed } from '@angular/core/testing'
import { UiAlertBoxComponent } from './ui-alert-box.component'

describe('UiAlertBoxComponent', () => {
  let component: UiAlertBoxComponent
  let fixture: ComponentFixture<UiAlertBoxComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UiAlertBoxComponent]
    }).compileComponents()

    fixture = TestBed.createComponent(UiAlertBoxComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  it('should display title and message', () => {
    fixture.componentRef.setInput('title', 'Test Title')
    fixture.componentRef.setInput('message', 'Test Message')
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Test Title')
    expect(compiled.textContent).toContain('Test Message')
  })
})
