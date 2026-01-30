import { ComponentFixture, TestBed } from '@angular/core/testing'
import { AlertBoxComponent } from './alert-box.component'

describe('AlertBoxComponent', () => {
  let component: AlertBoxComponent
  let fixture: ComponentFixture<AlertBoxComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlertBoxComponent]
    }).compileComponents()

    fixture = TestBed.createComponent(AlertBoxComponent)
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
