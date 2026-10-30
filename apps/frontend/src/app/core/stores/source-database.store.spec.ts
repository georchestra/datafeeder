import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { ApiConfiguration } from '../api/api-configuration'
import { SourceDatabaseStore } from './source-database.store'

const URL = 'http://localhost:8000/source-databases/'

describe('SourceDatabaseStore', () => {
  let store: SourceDatabaseStore
  let httpMock: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        }
      ]
    })
    store = TestBed.inject(SourceDatabaseStore)
    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => httpMock.verify())

  it('should load the source databases', async () => {
    const loaded = store.load()
    httpMock.expectOne(URL).flush([{ key: 'BAN', type: 'direct_access' }])
    await loaded

    expect(store.find('BAN')?.type).toBe('direct_access')
    expect(store.find('OTHER')).toBeNull()
  })

  it('should reload on each call and empty the list after a failure', async () => {
    const loaded = store.load()
    httpMock.expectOne(URL).flush([{ key: 'BAN', type: 'direct_access' }])
    await loaded

    const failed = store.load()
    httpMock
      .expectOne(URL)
      .flush(null, { status: 403, statusText: 'Forbidden' })
    await failed

    expect(store.sourceDatabases()).toEqual([])
  })

  it('should load the schemas of a database', async () => {
    const loaded = store.loadSchemas('BAN')
    httpMock
      .expectOne(`${URL}BAN/tables`)
      .flush([{ schema_name: 'geo', tables: ['rivers'] }])
    await loaded

    expect(store.schemas()).toEqual([
      { schema_name: 'geo', tables: ['rivers'] }
    ])
  })

  it('should keep the schemas of the last requested database only', async () => {
    const first = store.loadSchemas('DB_1')
    const second = store.loadSchemas('DB_2')
    httpMock
      .expectOne(`${URL}DB_2/tables`)
      .flush([{ schema_name: 'two', tables: [] }])
    httpMock
      .expectOne(`${URL}DB_1/tables`)
      .flush([{ schema_name: 'one', tables: [] }])
    await Promise.all([first, second])

    expect(store.schemas()).toEqual([{ schema_name: 'two', tables: [] }])
  })

  it('should empty the schemas without a key or after a failure', async () => {
    await store.loadSchemas('')
    httpMock.expectNone(() => true)
    expect(store.schemas()).toEqual([])

    const failed = store.loadSchemas('BAN')
    httpMock
      .expectOne(`${URL}BAN/tables`)
      .flush(null, { status: 503, statusText: 'Service Unavailable' })
    await failed
    expect(store.schemas()).toEqual([])
  })
})
