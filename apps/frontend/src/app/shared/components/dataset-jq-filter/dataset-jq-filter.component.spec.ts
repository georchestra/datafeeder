import { ComponentRef } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { DatasetJqFilterComponent } from './dataset-jq-filter.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import type { StagingMetadataResponse } from '../../../core/api/models'

const buildMetadata = (
  overrides: Partial<StagingMetadataResponse> = {}
): StagingMetadataResponse =>
  ({
    file_type: 'json',
    ...overrides
  } as StagingMetadataResponse)

describe('DatasetJqFilterComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DatasetJqFilterComponent,
        TranslateTestingModule.withTranslations({
          en: { 'import.configuration.jqFilter': 'JQ filter' }
        }).withDefaultLanguage('en')
      ]
    }).compileComponents()
  })

  it('shows the disabled jq filter field prefilled with "." for a json source', () => {
    const fixture = TestBed.createComponent(DatasetJqFilterComponent)
    const ref = fixture.componentRef as ComponentRef<DatasetJqFilterComponent>
    ref.setInput('metadata', buildMetadata({ file_type: 'json' }))
    fixture.detectChanges()

    const textarea: HTMLTextAreaElement =
      fixture.nativeElement.querySelector('textarea')
    expect(textarea).toBeTruthy()
    expect(textarea.value).toBe('.')
    expect(textarea.disabled).toBe(true)
  })

  it('does not render for a non-json source', () => {
    const fixture = TestBed.createComponent(DatasetJqFilterComponent)
    const ref = fixture.componentRef as ComponentRef<DatasetJqFilterComponent>
    ref.setInput('metadata', buildMetadata({ file_type: 'geojson' }))
    fixture.detectChanges()

    expect(fixture.nativeElement.querySelector('textarea')).toBeFalsy()
  })
})
