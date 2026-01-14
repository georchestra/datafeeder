import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { DatasetConfigurationComponent } from './dataset-configuration.component'
import { TranslateTestingModule } from 'ngx-translate-testing'
import { TranslateMessageFormatCompiler } from 'ngx-translate-messageformat-compiler'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'

describe('DatasetConfigurationComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DatasetConfigurationComponent,
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
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance
    expect(component).toBeTruthy()
  })

  it('should display loading text when no metadata', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Loading data...')
  })

  it('should display title heading when metadata is loaded', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance

    const mockMetadata: StagingMetadataResponse = {
      title: 'Test Dataset',
      columns: [{ name: 'col1', type: 'string' }]
    }

    component.metadata.set(mockMetadata)
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Dataset Title')
  })

  it('should populate form title with metadata title', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance

    const mockMetadata: StagingMetadataResponse = {
      title: 'My Test Dataset',
      columns: [{ name: 'col1', type: 'string' }]
    }

    component.metadata.set(mockMetadata)
    fixture.detectChanges()

    expect(component.form.get('title')?.value).toBe('My Test Dataset')
  })

  it('should use default title when metadata has no title', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance

    const mockMetadata: StagingMetadataResponse = {
      title: '',
      columns: [{ name: 'col1', type: 'string' }]
    }

    component.metadata.set(mockMetadata)
    fixture.detectChanges()

    expect(component.form.get('title')?.value).toBe('Untitled')
  })

  it('should compute displayed columns based on metadata', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Should be empty when no metadata
    let displayedColumns = component.displayedColumns()
    expect(displayedColumns).toEqual([])

    // Should display columns when metadata is set
    const mockMetadata: StagingMetadataResponse = {
      title: 'Test Dataset',
      columns: [
        { name: 'firstName', type: 'string' },
        { name: 'lastName', type: 'string' },
        { name: 'age', type: 'integer' }
      ]
    }

    component.metadata.set(mockMetadata)
    fixture.detectChanges()

    displayedColumns = component.displayedColumns()
    expect(displayedColumns).toEqual(['firstName', 'lastName', 'age'])
  })

  it('should manage datasource with preview data', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    // Should be empty when no preview data
    let dataSource = component.dataSource()
    expect(dataSource).toEqual([])

    // Should populate datasource with preview data
    const mockPreview: StagingPreviewResponse = {
      data: [
        { firstName: 'John', lastName: 'Doe', age: 30 },
        { firstName: 'Jane', lastName: 'Smith', age: 28 }
      ]
    }

    component.preview.set(mockPreview)
    fixture.detectChanges()

    dataSource = component.dataSource()
    expect(dataSource).toEqual(mockPreview.data)
  })

  it('should display loading message', () => {
    const fixture = TestBed.createComponent(DatasetConfigurationComponent)
    fixture.detectChanges()
    const compiled = fixture.nativeElement as HTMLElement
    expect(compiled.textContent).toContain('Loading data...')
  })
})
