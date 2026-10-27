import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { getCustomTranslations } from 'geonetwork-ui'
import { vi } from 'vitest'
import { DatafeederTranslateLoader } from './translate.loader'

vi.mock('geonetwork-ui', async (importOriginal) => ({
  ...(await importOriginal<typeof import('geonetwork-ui')>()),
  getCustomTranslations: vi.fn()
}))

describe('DatafeederTranslateLoader', () => {
  let loader: DatafeederTranslateLoader
  let httpMock: HttpTestingController

  beforeEach(() => {
    vi.mocked(getCustomTranslations).mockReturnValue({})
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

  it('applies the translation overrides from the configuration last', () => {
    vi.mocked(getCustomTranslations).mockReturnValue({
      overridden: 'TOML',
      tomlOnly: 'TOML'
    })
    let result: unknown
    loader.getTranslation('fr').subscribe((t) => (result = t))

    httpMock
      .expectOne('./assets/i18n/gn-ui/fr.json')
      .flush({ gnOnly: 'GN', overridden: 'GN' })
    httpMock
      .expectOne('./assets/i18n/fr.json')
      .flush({ dfOnly: 'DF', overridden: 'DF' })

    expect(getCustomTranslations).toHaveBeenCalledWith('fr')
    expect(result).toEqual({
      gnOnly: 'GN',
      dfOnly: 'DF',
      overridden: 'TOML',
      tomlOnly: 'TOML'
    })
  })
})
