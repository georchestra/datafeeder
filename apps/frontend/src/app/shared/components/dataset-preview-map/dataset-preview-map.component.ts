import { Component, effect, input, signal } from '@angular/core'
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

  constructor() {
    effect(() => {
      const data = this.geojson()
      if (!data?.features?.length) {
        this.mapContext.set(null)
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

    this.mapContext.set({
      layers: [layer],
      view: view ?? null
    })
  }
}
