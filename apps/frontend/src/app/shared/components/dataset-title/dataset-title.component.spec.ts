import { ComponentRef } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { DatasetTitleComponent } from './dataset-title.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type { StagingMetadataResponse } from '../../../core/api/models'

const buildMetadata = (
  overrides: Partial<StagingMetadataResponse> = {}
): StagingMetadataResponse =>
  ({
    title: 'Existing title',
    has_final_table: false,
    ...overrides
  } as StagingMetadataResponse)

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

  it('disables the title control when reconfiguring an existing dataset', () => {
    const fixture = TestBed.createComponent(DatasetTitleComponent)
    const ref = fixture.componentRef as ComponentRef<DatasetTitleComponent>
    ref.setInput('metadata', buildMetadata())
    ref.setInput('isReconfiguring', true)
    fixture.detectChanges()

    expect(fixture.componentInstance.form.controls.title.disabled).toBe(true)
  })

  it('keeps the title control enabled for a fresh dataset', () => {
    const fixture = TestBed.createComponent(DatasetTitleComponent)
    const ref = fixture.componentRef as ComponentRef<DatasetTitleComponent>
    ref.setInput('metadata', buildMetadata())
    ref.setInput('isReconfiguring', false)
    fixture.detectChanges()

    expect(fixture.componentInstance.form.controls.title.enabled).toBe(true)
  })
})
