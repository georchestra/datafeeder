import { TestBed } from '@angular/core/testing'
import { NoopAnimationsModule } from '@angular/platform-browser/animations'
import { DataSourceDbComponent } from './data-source-db.component'
import { TranslateTestingModule } from '../../testing/translate-testing.module'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'

describe('DataSourceDbComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DataSourceDbComponent,
        NoopAnimationsModule,
        TranslateTestingModule.withTranslations({
          en: {
            'import.dataSource.database.schema': 'Schema',
            'import.dataSource.database.table': 'Table',
            'import.dataSource.database.direct_access': 'Direct access'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should emit dbDataChanged when form values change', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    component.form.patchValue({ schema: 'geo', table: 'rivers' })

    expect(emittedValue).toEqual({ schema: 'geo', table: 'rivers', title: '' })
  })

  it('should fill the form from initialValue without emitting', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emitted = false

    component.dbDataChanged.subscribe(() => (emitted = true))
    fixture.componentRef.setInput('initialValue', {
      schema: 'geo',
      table: 'rivers'
    })
    fixture.detectChanges()

    expect(component.form.value).toEqual({
      schema: 'geo',
      table: 'rivers',
      title: ''
    })
    expect(emitted).toBe(false)
  })

  it('should show the source database with its access type', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    fixture.componentRef.setInput('sourceDatabase', {
      key: 'BAN',
      label: 'Base Adresse Nationale',
      type: 'direct_access'
    })
    fixture.detectChanges()

    const chip = fixture.nativeElement.querySelector(
      '[data-test="source-database"]'
    )
    expect(chip.textContent).toContain('BAN')
    expect(chip.textContent).toContain('Base Adresse Nationale')
    expect(chip.textContent).toContain('Direct access')
  })

  it('should not show a source database when none is given', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-test="source-database"]')
    ).toBeNull()
  })

  it('should ask for a title only for a direct access database', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const titleInput = () =>
      fixture.nativeElement.querySelector('[data-test="source-database-title"]')

    fixture.componentRef.setInput('sourceDatabase', {
      key: 'DB',
      type: 'copy'
    })
    fixture.detectChanges()
    expect(titleInput()).toBeNull()

    fixture.componentRef.setInput('sourceDatabase', {
      key: 'BAN',
      type: 'direct_access'
    })
    fixture.detectChanges()
    expect(titleInput()).toBeTruthy()
  })

  it('should clear the title when the table changes', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    component.form.patchValue({ schema: 'geo', table: 'rivers' })
    component.form.controls.title.setValue('Rivers')
    expect(emittedValue.title).toBe('Rivers')

    component.form.controls.table.setValue('lakes')

    expect(component.form.controls.title.value).toBe('')
    expect(emittedValue).toEqual({ schema: 'geo', table: 'lakes', title: '' })
  })
})
