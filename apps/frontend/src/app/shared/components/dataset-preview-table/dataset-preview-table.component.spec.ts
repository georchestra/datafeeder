import { TestBed } from '@angular/core/testing'
import { DatasetPreviewTableComponent } from './dataset-preview-table.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'

describe('DatasetPreviewTableComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DatasetPreviewTableComponent,
        TranslateTestingModule.withTranslations({
          en: {
            'import.datasetConfiguration.previewTitle': 'Result Preview',
            'import.datasetPreviewTable.noDataAvailable': 'No data available',
            'import.columnAction.menu.filter': 'Filter column',
            'import.columnAction.menu.changeType': 'Change type',
            'import.columnAction.menu.remove': 'Remove column'
          }
        })
          .withDefaultLanguage('en')
          .withCompiler(new TranslateMessageFormatCompiler())
      ]
    }).compileComponents()
  })

  it('should create', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should not display content when metadata is null', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('.py-6')).toBeNull()
  })

  it('should render content when metadata exists', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)

    const mockMetadata: StagingMetadataResponse = {
      title: 'Test Dataset',
      columns: [{ original_name: 'col1' }]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    // Component should render its container when metadata exists
    expect(compiled.querySelector('div')).toBeTruthy()
  })

  it('should display empty message when metadata exists but no data', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
    const component = fixture.componentInstance

    const mockMetadata: StagingMetadataResponse = {
      title: 'Test Dataset',
      columns: [{ original_name: 'col1' }]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('No data available')
  })

  it('should display table with columns and data when both exist', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
    const component = fixture.componentInstance

    const mockMetadata: StagingMetadataResponse = {
      title: 'Test Dataset',
      columns: [
        { original_name: 'firstName' },
        { original_name: 'lastName' }
      ]
    }

    const mockPreview: StagingPreviewResponse = {
      data: [{ firstName: 'John', lastName: 'Doe' }]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.componentRef.setInput('preview', mockPreview)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.querySelector('table')).toBeTruthy()
    // Column names are rendered as <input> values inside ColumnHeaderComponent
    const headerInputs = Array.from(
      compiled.querySelectorAll<HTMLInputElement>('th input[type="text"]')
    ).map((el) => el.value)
    expect(headerInputs).toContain('firstName')
    expect(headerInputs).toContain('lastName')
    expect(compiled.textContent).toContain('John')
    expect(compiled.textContent).toContain('Doe')
  })
})
