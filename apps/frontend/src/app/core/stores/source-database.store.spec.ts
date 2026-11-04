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
})
