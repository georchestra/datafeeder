import { TestBed } from '@angular/core/testing'
import { DatasetPreviewTableComponent } from './dataset-preview-table.component'
import { TranslateTestingModule } from '../../testing/translate-testing.module'
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
            'import.datasetPreviewTable.allColumnsExcluded':
              'All columns are excluded. Restore at least one column.',
            'import.columnAction.menu.filter': 'Filter column',
            'import.columnAction.menu.changeType': 'Change type',
            'import.columnAction.menu.remove': 'Remove column',
            'import.columnHeader.error.duplicate': 'Choose a unique column name'
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
      columns: [{ original_name: 'firstName' }, { original_name: 'lastName' }]
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

  // --- T027: Remove/restore behavior in preview table ---

  it('should still render excluded column header in table', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)

    const mockMetadata: StagingMetadataResponse = {
      title: 'Dataset',
      columns: [
        { original_name: 'col1', excluded: false },
        { original_name: 'col2', excluded: true }
      ]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.componentRef.setInput('preview', {
      data: [{ col1: 'a', col2: 'b' }]
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const headerInputs = Array.from(
      compiled.querySelectorAll<HTMLInputElement>('th input[type="text"]')
    ).map((el) => el.value)
    // Both columns should appear
    expect(headerInputs).toContain('col1')
    expect(headerInputs).toContain('col2')
  })

  it('should apply greyed-out styling to data cells of excluded columns', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)

    const mockMetadata: StagingMetadataResponse = {
      title: 'Dataset',
      columns: [
        { original_name: 'col1', excluded: false },
        { original_name: 'col2', excluded: true }
      ]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.componentRef.setInput('preview', {
      data: [{ col1: 'a', col2: 'b' }]
    })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    // The excluded column's <td> cells should have opacity-50 class
    const excludedCell = compiled.querySelector('td.excluded-cell')
    expect(excludedCell).toBeTruthy()
  })

  it('should show all-excluded warning when every column is excluded', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)

    const mockMetadata: StagingMetadataResponse = {
      title: 'Dataset',
      columns: [
        { original_name: 'col1', excluded: true },
        { original_name: 'col2', excluded: true }
      ]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.componentRef.setInput('preview', { data: [] })
    fixture.detectChanges()

    const compiled = fixture.nativeElement as HTMLElement
    const warning = compiled.querySelector('[data-all-excluded-warning]')
    expect(warning).toBeTruthy()
  })

  it('should emit columnActionRequested with remove when remove action is triggered', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)

    const mockMetadata: StagingMetadataResponse = {
      title: 'Dataset',
      columns: [{ original_name: 'col1', excluded: false }]
    }

    fixture.componentRef.setInput('metadata', mockMetadata)
    fixture.componentRef.setInput('preview', { data: [{ col1: 'v' }] })
    fixture.detectChanges()

    const emitted: Array<{ originalName: string; action: string }> = []
    fixture.componentInstance.columnActionRequested.subscribe((e) =>
      emitted.push(e)
    )

    // Simulate the ColumnHeaderComponent emitting the action
    fixture.componentInstance.onColumnAction('col1', 'remove')

    expect(emitted).toEqual([{ originalName: 'col1', action: 'remove' }])
  })

  it('should emit columnNameValidationErrorChanged with error when onColumnNameValidationErrorChange is called with an error', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
    fixture.detectChanges()

    const emitted: Array<{ originalName: string; error: string | null }> = []
    fixture.componentInstance.columnNameValidationErrorChanged.subscribe((e) =>
      emitted.push(e)
    )

    fixture.componentInstance.onColumnNameValidationErrorChange(
      'col1',
      'Le nom ne peut pas être vide'
    )

    expect(emitted).toEqual([
      { originalName: 'col1', error: 'Le nom ne peut pas être vide' }
    ])
  })

  it('should emit columnNameValidationErrorChanged with null when error is cleared', () => {
    const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
    fixture.detectChanges()

    const emitted: Array<{ originalName: string; error: string | null }> = []
    fixture.componentInstance.columnNameValidationErrorChanged.subscribe((e) =>
      emitted.push(e)
    )

    fixture.componentInstance.onColumnNameValidationErrorChange('col1', null)

    expect(emitted).toEqual([{ originalName: 'col1', error: null }])
  })

  describe('join columns', () => {
    const metadata: StagingMetadataResponse = {
      title: 'Test Dataset',
      columns: [{ original_name: 'insee' }, { original_name: 'nom' }]
    }
    const preview: StagingPreviewResponse = {
      data: [{ insee: '59009', nom: 'source nom', population: 1000 }]
    }

    function create(joinColumns: string[], joinClashes: string[] = []) {
      const fixture = TestBed.createComponent(DatasetPreviewTableComponent)
      fixture.componentRef.setInput('metadata', metadata)
      fixture.componentRef.setInput('preview', preview)
      fixture.componentRef.setInput('joinColumns', joinColumns)
      fixture.componentRef.setInput('joinClashes', joinClashes)
      fixture.detectChanges()
      return fixture
    }

    it('renders joined columns after the source columns, read-only and green', () => {
      const fixture = create(['population'])
      const el = fixture.nativeElement as HTMLElement

      expect(fixture.componentInstance.displayedColumns()).toEqual([
        'insee',
        'nom',
        'join:population'
      ])
      const header = el.querySelector('[data-join-header]')!
      expect(header.textContent).toContain('population')
      expect(header.querySelector('[data-action-button]')).toBeNull()
      const cell = el.querySelector('[data-join-cell]')!
      expect(cell.textContent?.trim()).toBe('1000')
      expect(cell.classList).toContain('!bg-green-50')
    })

    it('includes joined columns in the names checked for duplicates', () => {
      const fixture = create(['population'])
      expect(fixture.componentInstance.allDisplayNames()).toEqual([
        'insee',
        'nom',
        'population'
      ])
    })

    it('flags the source column clashing with a joined one and hides the joined values', () => {
      const fixture = create(['nom'], ['nom'])
      const el = fixture.nativeElement as HTMLElement

      const errors = Array.from(el.querySelectorAll('[data-name-error]'))
      expect(errors).toHaveLength(1)
      expect(errors[0].closest('[data-join-header]')).toBeNull()
      expect(errors[0].textContent).toContain('Choose a unique column name')
      expect(el.querySelector('[data-join-cell]')!.textContent?.trim()).toBe('')
    })

    it('flags a joined column clashing with no source column', () => {
      const fixture = create(['geom'], ['geom'])
      const el = fixture.nativeElement as HTMLElement

      expect(
        el.querySelector('[data-join-header] [data-name-error]')?.textContent
      ).toContain('Choose a unique column name')
    })
  })
})
