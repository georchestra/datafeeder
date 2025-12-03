import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { ImportComponent } from './import.component'

describe('ImportComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImportComponent, NoopAnimationsModule]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(ImportComponent)
    expect(fixture.componentInstance).toBeTruthy()
  })

  it('should display tab labels', () => {
    const fixture = TestBed.createComponent(ImportComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Ajouter un jeu de donnée')
  })

  it('should render data import wizard', () => {
    const fixture = TestBed.createComponent(ImportComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-data-import-wizard')).toBeTruthy()
  })
})
