import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { By } from '@angular/platform-browser'
import { DatasetJoinComponent } from './dataset-join.component'
import { TranslateTestingModule } from '../../testing/translate-testing.module'
import { ApiConfiguration } from '../../../core/api/api-configuration'
import type { JoinableTable, JoinConfig } from '../../../core/api/models'

const ROOT = 'http://localhost:8000'
const TABLES_URL = `${ROOT}/ingestion/integrity-links/joinable-tables`
const columnsUrl = (id: string) =>
  `${ROOT}/ingestion/integrity-links/${id}/joinable-columns`
const settle = () => new Promise((resolve) => setTimeout(resolve))

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
  integrity_link_id: 'link-1',
  source_column: 'insee',
  target_column: 'code_insee',
  columns: ['nom']
}

describe('DatasetJoinComponent', () => {
  let httpMock: HttpTestingController

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DatasetJoinComponent,
        TranslateTestingModule.withTranslations({ en: {} }).withDefaultLanguage(
          'en'
        )
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: ROOT } }
      ]
    }).compileComponents()

    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => httpMock.verify())

  async function create(join: JoinConfig | null, targetColumns: string[] = []) {
    const fixture = TestBed.createComponent(DatasetJoinComponent)
    fixture.componentRef.setInput('sourceColumns', [
      { original_name: 'insee', new_name: 'code' },
      { original_name: 'pop' }
    ])
    fixture.componentRef.setInput('join', join)
    fixture.detectChanges()
    httpMock.expectOne(TABLES_URL).flush(TABLES)
    await settle()
    if (join) {
      httpMock
        .expectOne(columnsUrl(join.integrity_link_id))
        .flush(targetColumns.map((column_name) => ({ column_name })))
      await settle()
    }
    fixture.detectChanges()
    return fixture
  }

  function emitted(fixture: { componentInstance: DatasetJoinComponent }) {
    const joins: JoinConfig[] = []
    fixture.componentInstance.joinChange.subscribe((j) => joins.push(j))
    return joins
  }

  it('loads the tables, and the columns of the saved join table', async () => {
    const fixture = await create(JOIN, ['code_insee', 'nom'])
    expect(fixture.componentInstance.tables()).toEqual(TABLES)
    expect(fixture.componentInstance.targetColumns()).toEqual([
      'code_insee',
      'nom'
    ])
  })

  it('resolves the selected table from the join dataset id', async () => {
    const fixture = await create(JOIN)
    expect(fixture.componentInstance.selectedTable()).toBe(TABLES[0])
    expect(
      fixture.nativeElement.querySelector('[data-table-select]').textContent
    ).toContain('Communes')
  })

  it('lists tables with the dataset title and the table name as subtitle', async () => {
    const fixture = await create(null)
    fixture.componentInstance.tableListOpen.set(true)
    fixture.detectChanges()

    const options = document.querySelectorAll('[data-table-option]')
    expect(options.length).toBe(2)
    expect(options[0].textContent).toContain('Communes')
    expect(options[0].textContent).toContain('communes')
    expect(options[1].textContent).toContain('regions')
  })

  it('keeps the source key and resets the rest when another table is picked', async () => {
    const fixture = await create(JOIN, ['code_insee', 'nom'])
    const joins = emitted(fixture)

    await fixture.componentInstance.selectTable(TABLES[0])
    expect(joins).toEqual([])

    const selecting = fixture.componentInstance.selectTable(TABLES[1])
    expect(joins).toEqual([
      {
        integrity_link_id: 'link-2',
        source_column: 'insee',
        target_column: '',
        columns: []
      }
    ])
    expect(fixture.componentInstance.targetColumns()).toEqual([])
    httpMock.expectOne(columnsUrl('link-2')).flush([{ column_name: 'code' }])
    await selecting
    expect(fixture.componentInstance.targetColumns()).toEqual(['code'])
  })

  it('labels source key choices with the displayed column name', async () => {
    const fixture = await create(null)
    expect(fixture.componentInstance.sourceChoices()).toEqual([
      { value: '', label: '-' },
      { value: 'insee', label: 'code' },
      { value: 'pop', label: 'pop' }
    ])
  })

  it('emits the join with the selected keys', async () => {
    const fixture = await create({ ...JOIN, target_column: '', columns: [] })
    const joins = emitted(fixture)

    fixture.componentInstance.update({ target_column: 'code_insee' })

    expect(joins).toEqual([{ ...JOIN, columns: [] }])
  })

  it('hides the columns to add until both keys are selected', async () => {
    const fixture = await create({ ...JOIN, target_column: '', columns: [] })
    expect(
      fixture.nativeElement.querySelector('[data-columns-to-add]')
    ).toBeNull()

    fixture.componentRef.setInput('join', JOIN)
    fixture.detectChanges()
    expect(
      fixture.nativeElement.querySelector('[data-columns-to-add]')
    ).not.toBeNull()
  })

  it('only offers columns not added yet, without id_datafeeder', async () => {
    const fixture = await create(JOIN, [
      'id_datafeeder',
      'code_insee',
      'nom',
      'geom'
    ])
    expect(fixture.componentInstance.availableColumns()).toEqual([
      { value: 'code_insee', label: 'code_insee' },
      { value: 'geom', label: 'geom' }
    ])
  })

  it('hides the add dropdown when no column is left', async () => {
    const fixture = await create(JOIN, ['nom'])
    expect(fixture.nativeElement.querySelector('[data-column-add]')).toBeNull()
    expect(
      fixture.nativeElement.querySelectorAll('[data-join-column]').length
    ).toBe(1)
  })

  it('emits the join with an added column and ignores the empty choice', async () => {
    const fixture = await create(JOIN, ['nom', 'geom'])
    const joins = emitted(fixture)

    fixture.componentInstance.addColumn('')
    fixture.componentInstance.addColumn('geom')

    expect(joins).toEqual([{ ...JOIN, columns: ['nom', 'geom'] }])
  })

  it('resets the add dropdown so a column offered back is not shown as selected', async () => {
    const fixture = await create(JOIN, ['nom', 'geom'])
    fixture.debugElement
      .query(By.css('[data-column-add]'))
      .componentInstance.onSelectValue({ value: 'geom', label: 'geom' })
    fixture.detectChanges()

    expect(
      fixture.nativeElement.querySelector('[data-column-add] button')
        .textContent
    ).not.toContain('geom')
  })

  it('emits the join without a column when it is clicked', async () => {
    const fixture = await create(JOIN, ['nom'])
    const joins = emitted(fixture)

    fixture.nativeElement.querySelector('[data-join-column]').click()

    expect(joins).toEqual([{ ...JOIN, columns: [] }])
  })

  it('emits loadError with the backend detail when the tables fail to load', async () => {
    const fixture = TestBed.createComponent(DatasetJoinComponent)
    const errors: string[] = []
    fixture.componentInstance.loadError.subscribe((e) => errors.push(e))
    fixture.componentRef.setInput('join', JOIN)
    fixture.detectChanges()

    httpMock
      .expectOne(TABLES_URL)
      .flush({ detail: 'Boom' }, { status: 500, statusText: 'Error' })
    await settle()

    expect(errors).toEqual(['Boom'])
    httpMock.expectNone(columnsUrl('link-1'))
  })

  it('emits a generic loadError when the table columns fail to load', async () => {
    const fixture = await create(null)
    const errors: string[] = []
    fixture.componentInstance.loadError.subscribe((e) => errors.push(e))

    const selecting = fixture.componentInstance.selectTable(TABLES[1])
    httpMock
      .expectOne(columnsUrl('link-2'))
      .flush(null, { status: 500, statusText: 'Error' })
    await selecting

    expect(errors).toEqual(['import.dataSource.genericError'])
  })
})
