import { Component, effect, input, model, signal } from '@angular/core'
import { MapContainerComponent } from 'geonetwork-ui'
import type { MapContext, MapContextLayerGeojson } from '@geospatial-sdk/core'
import { createViewFromLayer } from '@geospatial-sdk/core'
import type { FeatureCollection } from 'geojson'

@Component({
  selector: 'app-dataset-preview-map',
  imports: [MapContainerComponent],
  templateUrl: './dataset-preview-map.component.html',
  styleUrl: './dataset-preview-map.component.scss'
})
export class DatasetPreviewMapComponent {
  geojson = input<FeatureCollection | null>(null)
  mapContext = signal<MapContext | null>(null)
  hasExtentError = model<boolean>(false)

  constructor() {
    effect(() => {
      const data = this.geojson()
      if (!data?.features?.length) {
        this.mapContext.set(null)
        this.hasExtentError.set(false)
        return
      }
      this.buildMapContext(data)
    })
  }

  private async buildMapContext(data: FeatureCollection): Promise<void> {
    const layer: MapContextLayerGeojson = {
      type: 'geojson',
      data: data
    }

    const view = await createViewFromLayer(layer)

    // Validate extent for EPSG:4326, otherwhise the map will not render
    const validView = this.validateExtent(view)

    this.mapContext.set({
      layers: [layer],
      view: validView ?? null
    })
  }

  private validateExtent(view: any): any {
    if (!view?.extent) {
      this.hasExtentError.set(false)
      return view
    }

    const [minX, minY, maxX, maxY] = view.extent

    const isValidExtent =
      minX >= -180 &&
      minX <= 180 &&
      maxX >= -180 &&
      maxX <= 180 &&
      minY >= -90 &&
      minY <= 90 &&
      maxY >= -90 &&
      maxY <= 90 &&
      minX <= maxX &&
      minY <= maxY

    if (!isValidExtent) {
      this.hasExtentError.set(true)
      const viewWithoutExtent = { ...view }
      delete viewWithoutExtent.extent
      return Object.keys(viewWithoutExtent).length > 0
        ? viewWithoutExtent
        : null
    }

    this.hasExtentError.set(false)
    return view
  }
}
