import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { DatasetTitleComponent } from './dataset-title.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'

describe('DatasetTitleComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DatasetTitleComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'import.configuration.datasetTitle': 'Dataset Title',
            'import.configuration.loading': 'Loading data...',
            'import.datasetConfiguration.untitled': 'Untitled'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DatasetTitleComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })
})
