import { TestBed } from '@angular/core/testing'
import { MatTooltip } from '@angular/material/tooltip'
import { By } from '@angular/platform-browser'
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

  it('should emit dbDataChanged when the values change', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    component.selectSchema('geo')
    component.selectTable('rivers')
    fixture.detectChanges()

    expect(emittedValue).toEqual({
      key: '',
      schema: 'geo',
      table: 'rivers',
      title: ''
    })
  })

  it('should fill the form and the database from initialValue', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'DB_1', type: 'copy' },
      { key: 'DB_2', type: 'copy' }
    ])
    fixture.componentRef.setInput('initialValue', {
      key: 'DB_2',
      schema: 'geo',
      table: 'rivers'
    })
    fixture.detectChanges()

    expect(emittedValue).toEqual({
      key: 'DB_2',
      schema: 'geo',
      table: 'rivers',
      title: ''
    })
  })

  it('should list the databases until one is selected', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'DB_1', type: 'copy' },
      { key: 'DB_2', type: 'direct_access' }
    ])
    fixture.detectChanges()

    const rows = fixture.nativeElement.querySelectorAll(
      '[data-test="source-database-list"] button'
    )
    expect(rows.length).toBe(2)
    expect(component.sourceDatabase()).toBeNull()

    rows[1].click()
    fixture.detectChanges()

    expect(component.sourceDatabase()?.key).toBe('DB_2')
    expect(emittedValue.key).toBe('DB_2')
    expect(
      fixture.nativeElement.querySelector('[data-test="source-database-list"]')
    ).toBeNull()
  })

  it('should go back to the list and clear the inputs when the selected database is clicked', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'DB_1', type: 'copy' }
    ])
    component.select('DB_1')
    component.selectSchema('geo')
    component.selectTable('rivers')
    fixture.detectChanges()

    fixture.nativeElement.querySelector('[data-test="source-database"]').click()
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-test="source-database-list"]')
    ).toBeTruthy()
    expect(emittedValue).toEqual({
      key: '',
      schema: '',
      table: '',
      title: ''
    })
  })

  it('should show the source database with its access type', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'BAN', label: 'Base Adresse Nationale', type: 'direct_access' }
    ])
    fixture.componentInstance.select('BAN')
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

    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'DB', type: 'copy' },
      { key: 'BAN', type: 'direct_access' }
    ])
    fixture.componentInstance.select('DB')
    fixture.detectChanges()
    expect(titleInput()).toBeNull()

    fixture.componentInstance.select('BAN')
    fixture.detectChanges()
    expect(titleInput()).toBeTruthy()
  })

  it('should clear the title when the table changes', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    component.selectSchema('geo')
    component.selectTable('rivers')
    component.setTitle('Rivers')
    fixture.detectChanges()
    expect(emittedValue.title).toBe('Rivers')

    component.selectTable('lakes')
    fixture.detectChanges()

    expect(emittedValue).toEqual({
      key: '',
      schema: 'geo',
      table: 'lakes',
      title: ''
    })
  })

  it('should enable the table once a schema is set, and the title once both are', async () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    const input = (name: string) =>
      fixture.nativeElement.querySelector(
        `[data-test="${name}"] input, [data-test="${name}"] button`
      )

    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'BAN', type: 'direct_access' }
    ])
    component.select('BAN')
    fixture.detectChanges()
    await fixture.whenStable()
    expect(input('source-database-table').disabled).toBe(true)
    expect(input('source-database-title').disabled).toBe(true)

    component.selectSchema('geo')
    fixture.detectChanges()
    await fixture.whenStable()
    expect(input('source-database-table').disabled).toBe(false)
    expect(input('source-database-title').disabled).toBe(true)

    component.selectTable('rivers')
    fixture.detectChanges()
    await fixture.whenStable()
    expect(input('source-database-title').disabled).toBe(false)
  })

  it('should show the full database name in a tooltip', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    fixture.componentRef.setInput('sourceDatabases', [
      { key: 'BAN', label: 'Base Adresse Nationale', type: 'copy' }
    ])
    fixture.detectChanges()

    const tooltip = fixture.debugElement
      .query(By.directive(MatTooltip))
      .injector.get(MatTooltip)
    expect(tooltip.message).toBe('BAN Base Adresse Nationale')
  })

  it('should show an empty state when no database is configured', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-test="source-database-empty"]')
    ).toBeTruthy()
    expect(
      fixture.nativeElement.querySelectorAll(
        '[data-test="source-database-list"] button'
      ).length
    ).toBe(0)
  })

  it('should offer the schemas, then the tables of the selected schema', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    fixture.componentRef.setInput('sourceSchemas', [
      { schema_name: 'geo', tables: ['rivers', 'lakes'] },
      { schema_name: 'admin', tables: ['cities'] }
    ])

    expect(component.schemaChoices().map((c) => c.value)).toEqual([
      '',
      'geo',
      'admin'
    ])
    expect(component.tableChoices().map((c) => c.value)).toEqual([''])

    component.selectSchema('geo')

    expect(component.tableChoices().map((c) => c.value)).toEqual([
      '',
      'rivers',
      'lakes'
    ])
  })

  it('should clear the table when the schema changes', () => {
    const fixture = TestBed.createComponent(DataSourceDbComponent)
    const component = fixture.componentInstance
    let emittedValue: any

    component.dbDataChanged.subscribe((value) => (emittedValue = value))
    component.selectSchema('geo')
    component.selectTable('rivers')

    component.selectSchema('admin')
    fixture.detectChanges()

    expect(emittedValue).toEqual({
      key: '',
      schema: 'admin',
      table: '',
      title: ''
    })
  })
})
