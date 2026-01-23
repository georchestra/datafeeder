import { ComponentFixture, TestBed } from '@angular/core/testing'
import { Component, input } from '@angular/core'
import { By } from '@angular/platform-browser'
import type { FeatureCollection, Point } from 'geojson'
import type { MapContext } from '@geospatial-sdk/core'
import { DatasetPreviewMapComponent } from './dataset-preview-map.component'

// Mock createViewFromLayer - this is hoisted so it works
vi.mock('@geospatial-sdk/core', () => ({
  createViewFromLayer: vi.fn().mockResolvedValue({
    extent: [0, 0, 1, 1]
  })
}))

// Mock geonetwork-ui with inline component definition
vi.mock('geonetwork-ui', () => ({
  MapContainerComponent: {
    // Empty stub - the real mock component is provided in TestBed
  }
}))

// Mock MapContainerComponent for TestBed override
@Component({
  selector: 'gn-ui-map-container',
  template: '<div class="mock-map-container"></div>',
  standalone: true
})
class MockMapContainerComponent {
  context = input<MapContext | null>(null)
}

describe('DatasetPreviewMapComponent', () => {
  let component: DatasetPreviewMapComponent
  let fixture: ComponentFixture<DatasetPreviewMapComponent>

  const mockGeojson: FeatureCollection<Point> = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [0, 0]
        },
        properties: { name: 'Test Point' }
      }
    ]
  }

  const emptyGeojson: FeatureCollection = {
    type: 'FeatureCollection',
    features: []
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetPreviewMapComponent, MockMapContainerComponent]
    })
      .overrideComponent(DatasetPreviewMapComponent, {
        set: {
          imports: [MockMapContainerComponent]
        }
      })
      .compileComponents()

    fixture = TestBed.createComponent(DatasetPreviewMapComponent)
    component = fixture.componentInstance
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  it('should initialize with null mapContext', () => {
    expect(component.mapContext()).toBeNull()
  })

  it('should initialize with null geojson input', () => {
    expect(component.geojson()).toBeNull()
  })

  it('should not render map container when mapContext is null', () => {
    fixture.detectChanges()

    const mapContainer = fixture.debugElement.query(
      By.css('gn-ui-map-container')
    )
    expect(mapContainer).toBeFalsy()
  })

  it('should set mapContext to null when geojson is null', async () => {
    fixture.componentRef.setInput('geojson', null)
    fixture.detectChanges()
    await fixture.whenStable()

    expect(component.mapContext()).toBeNull()
  })

  it('should set mapContext to null when geojson has no features', async () => {
    fixture.componentRef.setInput('geojson', emptyGeojson)
    fixture.detectChanges()
    await fixture.whenStable()

    expect(component.mapContext()).toBeNull()
  })

  it('should build mapContext when valid geojson is provided', async () => {
    fixture.componentRef.setInput('geojson', mockGeojson)
    fixture.detectChanges()
    await fixture.whenStable()
    // Allow async buildMapContext to complete
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.mapContext()).not.toBeNull()
    expect(component.mapContext()?.layers).toHaveLength(1)
    expect(component.mapContext()?.layers[0].type).toBe('geojson')
  })

  it('should render map container when mapContext is set', async () => {
    fixture.componentRef.setInput('geojson', mockGeojson)
    fixture.detectChanges()
    await fixture.whenStable()
    // Allow async buildMapContext to complete
    await new Promise((resolve) => setTimeout(resolve, 10))
    fixture.detectChanges()

    const mapContainer = fixture.debugElement.query(
      By.css('gn-ui-map-container')
    )
    expect(mapContainer).toBeTruthy()
  })

  it('should include geojson data in the map layer', async () => {
    fixture.componentRef.setInput('geojson', mockGeojson)
    fixture.detectChanges()
    await fixture.whenStable()
    // Allow async buildMapContext to complete
    await new Promise((resolve) => setTimeout(resolve, 10))

    const context = component.mapContext()
    expect(context?.layers[0]).toEqual({
      type: 'geojson',
      data: mockGeojson
    })
  })

  it('should update mapContext when geojson changes from valid to empty', async () => {
    // First set valid geojson
    fixture.componentRef.setInput('geojson', mockGeojson)
    fixture.detectChanges()
    await fixture.whenStable()
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(component.mapContext()).not.toBeNull()

    // Then set to empty
    fixture.componentRef.setInput('geojson', emptyGeojson)
    fixture.detectChanges()
    await fixture.whenStable()

    expect(component.mapContext()).toBeNull()
  })

  it('should have view in mapContext when valid geojson is provided', async () => {
    fixture.componentRef.setInput('geojson', mockGeojson)
    fixture.detectChanges()
    await fixture.whenStable()
    // Allow async buildMapContext to complete
    await new Promise((resolve) => setTimeout(resolve, 10))

    const context = component.mapContext()
    expect(context?.view).toBeDefined()
  })
})
