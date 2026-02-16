import { ComponentFixture, TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { DatasetConfigurationComponent } from './dataset-configuration.component'
import { TranslateModule } from '@ngx-translate/core'
import { provideApiConfiguration } from '../../../core/api/api-configuration'
import type { StagingMetadataResponse } from '../../../core/api/models'

describe('DatasetConfigurationComponent', () => {
  let component: DatasetConfigurationComponent
  let fixture: ComponentFixture<DatasetConfigurationComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetConfigurationComponent, TranslateModule.forRoot()],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideApiConfiguration('/test')
      ]
    }).compileComponents()

    fixture = TestBed.createComponent(DatasetConfigurationComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  it('should initialize with empty signals', () => {
    expect(component.selectedProjection()).toBe('')
    expect(component.selectedXCol()).toBe(null)
    expect(component.selectedYCol()).toBe(null)
    expect(component.showError()).toBe(false)
  })

  it('should emit config when selecting projection', () => {
    const spy = vi.fn()
    component.configChanged.subscribe(spy)

    component.selectProjection('EPSG:4326')

    expect(component.selectedProjection()).toBe('EPSG:4326')
    expect(spy).toHaveBeenCalledWith({
      projection: 'EPSG:4326',
      colX: '',
      colY: ''
    })
  })

  it('should emit config when selecting X column', () => {
    const spy = vi.fn()
    component.configChanged.subscribe(spy)

    component.selectXCol('longitude')

    expect(component.selectedXCol()).toBe('longitude')
    expect(spy).toHaveBeenCalledWith({
      projection: '',
      colX: 'longitude',
      colY: ''
    })
  })

  it('should emit config when selecting Y column', () => {
    const spy = vi.fn()
    component.configChanged.subscribe(spy)

    component.selectYCol('latitude')

    expect(component.selectedYCol()).toBe('latitude')
    expect(spy).toHaveBeenCalledWith({
      projection: '',
      colX: '',
      colY: 'latitude'
    })
  })

  it('should switch X and Y columns', () => {
    const spy = vi.fn()
    component.configChanged.subscribe(spy)

    component.selectedXCol.set('lon')
    component.selectedYCol.set('lat')

    component.onSwitchXY()

    expect(component.selectedXCol()).toBe('lat')
    expect(component.selectedYCol()).toBe('lon')
    expect(spy).toHaveBeenCalled()
  })

  it('should compute columns from metadata', () => {
    const metadata: StagingMetadataResponse = {
      columns: [
        { name: 'id', type: 'integer' },
        { name: 'name', type: 'text' }
      ],
      force_projection: null
    }

    fixture.componentRef.setInput('metadata', metadata)
    fixture.detectChanges()

    const columns = component.columns()
    expect(columns.length).toBe(3) // '-' + 2 columns
    expect(columns[1].value).toBe('id')
    expect(columns[2].value).toBe('name')
  })

  it('should compute displayed columns from metadata', () => {
    const metadata: StagingMetadataResponse = {
      columns: [
        { name: 'col1', type: 'text' },
        { name: 'col2', type: 'integer' }
      ],
      force_projection: null
    }

    fixture.componentRef.setInput('metadata', metadata)
    fixture.detectChanges()

    const displayedColumns = component.displayedColumns()
    expect(displayedColumns).toEqual(['col1', 'col2'])
  })

  it('should show error when previewError is set', () => {
    fixture.componentRef.setInput('previewError', 'An error occurred')
    fixture.detectChanges()

    expect(component.showError()).toBe(true)
  })

  it('should initialize from metadata force_projection', () => {
    const metadata: StagingMetadataResponse = {
      columns: [],
      force_projection: {
        type: 'EPSG:4326',
        x_column: 'lon',
        y_column: 'lat'
      }
    }

    fixture.componentRef.setInput('metadata', metadata)
    fixture.detectChanges()

    expect(component.selectedProjection()).toBe('EPSG:4326')
    expect(component.selectedXCol()).toBe('lon')
    expect(component.selectedYCol()).toBe('lat')
  })
})
