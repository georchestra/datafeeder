import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { DataSourceSelectorComponent } from './data-source-selector.component'

describe('DataSourceSelectorComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataSourceSelectorComponent, NoopAnimationsModule]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should display the title', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain(
      'Choisissez par quel biais vous souhaitez importer votre donnée'
    )
  })

  it('should have url as default source type', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    expect(component.form.controls.sourceType.value).toBe('url')
  })

  it('should validate URL pattern - reject invalid URL', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.url.setValue('invalid')
    expect(component.form.controls.url.errors?.['pattern']).toBeTruthy()
  })

  it('should validate URL pattern - accept valid http URL', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.url.setValue('http://example.com')
    expect(component.form.controls.url.errors?.['pattern']).toBeFalsy()
  })

  it('should validate URL pattern - accept valid https URL', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    component.form.controls.url.setValue('https://example.com')
    expect(component.form.controls.url.errors?.['pattern']).toBeFalsy()
  })

  it('should emit sourceChanged on form changes', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.sourceChanged.subscribe((value) => (emittedValue = value))
    component.form.controls.url.setValue('https://test.com')

    expect(emittedValue).toEqual({ type: 'url', url: 'https://test.com' })
  })

  it('should sync input to form', () => {
    const fixture = TestBed.createComponent(DataSourceSelectorComponent)
    const component = fixture.componentInstance

    fixture.componentRef.setInput('sourceData', {
      type: 'url',
      url: 'https://initial.com'
    })
    fixture.detectChanges()

    expect(component.form.controls.url.value).toBe('https://initial.com')
  })
})
