import { TestBed } from '@angular/core/testing'
import { By } from '@angular/platform-browser'
import { DatasetJoinComponent } from './dataset-join.component'
import { TranslateTestingModule } from '../../testing/translate-testing.module'
import type { JoinableTable, JoinConfig } from '../../../core/api/models'

const TABLES: JoinableTable[] = [
  {
    id: 'link-1',
    integrity_title: 'Communes',
    table_schema: 'org_a',
    table_name: 'communes'
  },
  {
    id: 'link-2',
    integrity_title: null,
    table_schema: 'org_a',
    table_name: 'regions'
  }
]

const JOIN: JoinConfig = {
  table_schema: 'org_a',
  table_name: 'communes',
  source_column: 'insee',
  target_column: 'code_insee',
  columns: ['nom']
}

describe('DatasetJoinComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DatasetJoinComponent,
        TranslateTestingModule.withTranslations({ en: {} }).withDefaultLanguage(
          'en'
        )
      ]
    }).compileComponents()
  })

  function create(join: JoinConfig | null, targetColumns: string[] = []) {
    const fixture = TestBed.createComponent(DatasetJoinComponent)
    fixture.componentRef.setInput('tables', TABLES)
    fixture.componentRef.setInput('sourceColumns', [
      { original_name: 'insee', new_name: 'code' },
      { original_name: 'pop' }
    ])
    fixture.componentRef.setInput('targetColumns', targetColumns)
    fixture.componentRef.setInput('join', join)
    fixture.detectChanges()
    return fixture
  }

  it('resolves the selected table from schema and name', () => {
    const fixture = create(JOIN)
    expect(fixture.componentInstance.selectedTable()).toBe(TABLES[0])
    expect(
      fixture.nativeElement.querySelector('[data-table-select]').textContent
    ).toContain('Communes')
  })

  it('lists tables with the dataset title and the table name as subtitle', () => {
    const fixture = create(null)
    fixture.componentInstance.tableListOpen.set(true)
    fixture.detectChanges()

    const options = document.querySelectorAll('[data-table-option]')
    expect(options.length).toBe(2)
    expect(options[0].textContent).toContain('Communes')
    expect(options[0].textContent).toContain('communes')
    expect(options[1].textContent).toContain('regions')
  })

  it('emits tableChange only when another table is picked', () => {
    const fixture = create(JOIN)
    const emitted: JoinableTable[] = []
    fixture.componentInstance.tableChange.subscribe((t) => emitted.push(t))

    fixture.componentInstance.selectTable(TABLES[0])
    fixture.componentInstance.selectTable(TABLES[1])

    expect(emitted).toEqual([TABLES[1]])
  })

  it('labels source key choices with the displayed column name', () => {
    const fixture = create(null)
    expect(fixture.componentInstance.sourceChoices()).toEqual([
      { value: '', label: '-' },
      { value: 'insee', label: 'code' },
      { value: 'pop', label: 'pop' }
    ])
  })

  it('hides the columns to add until both keys are selected', () => {
    const fixture = create({ ...JOIN, target_column: '', columns: [] })
    expect(
      fixture.nativeElement.querySelector('[data-columns-to-add]')
    ).toBeNull()

    fixture.componentRef.setInput('join', JOIN)
    fixture.detectChanges()
    expect(
      fixture.nativeElement.querySelector('[data-columns-to-add]')
    ).not.toBeNull()
  })

  it('only offers columns not added yet, without id_datafeeder', () => {
    const fixture = create(JOIN, ['id_datafeeder', 'code_insee', 'nom', 'geom'])
    expect(fixture.componentInstance.availableColumns()).toEqual([
      { value: 'code_insee', label: 'code_insee' },
      { value: 'geom', label: 'geom' }
    ])
  })

  it('hides the add dropdown when no column is left', () => {
    const fixture = create(JOIN, ['nom'])
    expect(fixture.nativeElement.querySelector('[data-column-add]')).toBeNull()
    expect(
      fixture.nativeElement.querySelectorAll('[data-join-column]').length
    ).toBe(1)
  })

  it('emits columnAdd for a column and ignores the empty choice', () => {
    const fixture = create(JOIN, ['nom', 'geom'])
    const emitted: string[] = []
    fixture.componentInstance.columnAdd.subscribe((c) => emitted.push(c))

    fixture.componentInstance.addColumn('')
    fixture.componentInstance.addColumn('geom')

    expect(emitted).toEqual(['geom'])
  })

  it('resets the add dropdown so a column offered back is not shown as selected', () => {
    const fixture = create(JOIN, ['nom', 'geom'])
    fixture.debugElement
      .query(By.css('[data-column-add]'))
      .componentInstance.onSelectValue({ value: 'geom', label: 'geom' })
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-column-add] button')
        .textContent
    ).not.toContain('geom')
  })

  it('emits columnRemove when an added column is clicked', () => {
    const fixture = create(JOIN, ['nom'])
    const emitted: string[] = []
    fixture.componentInstance.columnRemove.subscribe((c) => emitted.push(c))

    fixture.nativeElement.querySelector('[data-join-column]').click()

    expect(emitted).toEqual(['nom'])
  })
})
