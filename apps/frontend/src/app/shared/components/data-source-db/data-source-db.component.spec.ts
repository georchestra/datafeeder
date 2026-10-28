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
            'import.dataSource.database.table': 'Table'
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

    expect(emittedValue).toEqual({ schema: 'geo', table: 'rivers' })
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

    expect(component.form.value).toEqual({ schema: 'geo', table: 'rivers' })
    expect(emitted).toBe(false)
  })
})
