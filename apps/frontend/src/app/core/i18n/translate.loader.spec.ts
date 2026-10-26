import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { DatafeederTranslateLoader } from './translate.loader'

describe('DatafeederTranslateLoader', () => {
  let loader: DatafeederTranslateLoader
  let httpMock: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DatafeederTranslateLoader
      ]
    })
    loader = TestBed.inject(DatafeederTranslateLoader)
    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => httpMock.verify())

  it('merges gn-ui and datafeeder translations, datafeeder taking precedence and empty values ignored', () => {
    let result: unknown
    loader.getTranslation('de_DE').subscribe((t) => (result = t))

    httpMock
      .expectOne('./assets/i18n/gn-ui/de.json')
      .flush({ gnOnly: 'GN', overridden: 'GN', emptyInDf: 'GN' })
    httpMock
      .expectOne('./assets/i18n/de.json')
      .flush({ dfOnly: 'DF', overridden: 'DF', emptyInDf: '' })

    expect(result).toEqual({
      gnOnly: 'GN',
      dfOnly: 'DF',
      overridden: 'DF',
      emptyInDf: 'GN'
    })
  })
})
