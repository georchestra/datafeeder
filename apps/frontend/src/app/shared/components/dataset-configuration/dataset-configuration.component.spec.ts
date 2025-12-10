import { TestBed } from '@angular/core/testing'
import { DatasetConfigurationComponent } from './dataset-configuration.component'

describe('DatasetConfigurationComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetConfigurationComponent]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should display placeholder text', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain(
      'Configuration du jeu de donnée - À venir'
    )
  })
})
