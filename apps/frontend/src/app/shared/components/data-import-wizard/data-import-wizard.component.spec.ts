import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { DataImportWizardComponent } from './data-import-wizard.component'

describe('DataImportWizardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataImportWizardComponent, NoopAnimationsModule]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should initialize with first tab selected', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.selectedTabIndex()).toBe(0)
  })

  it('should initialize with empty source data', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    expect(component.importData()).toEqual({
      source: { type: 'url', url: '' }
    })
  })

  it('should render both tab labels', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Ajouter un jeu de donnée')
    expect(compiled.textContent).toContain('Paramétrer le jeu de donnée')
  })

  it('should render tab icons', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    const icons = compiled.querySelectorAll('mat-icon')
    expect(icons.length).toBeGreaterThanOrEqual(2)
    expect(icons[0].textContent).toContain('add')
    expect(icons[1].textContent).toContain('settings')
  })

  it('should update import data when source changes', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance

    component.onSourceChanged({ type: 'url', url: 'https://test.com' })

    expect(component.importData().source).toEqual({
      type: 'url',
      url: 'https://test.com'
    })
  })

  it('should render data source selector in first tab', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-data-source-selector')).toBeTruthy()
  })

  it('should render dataset configuration in second tab', () => {
    const fixture = TestBed.createComponent(DataImportWizardComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Switch to second tab
    component.selectedTabIndex.set(1)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('app-dataset-configuration')).toBeTruthy()
  })
})
