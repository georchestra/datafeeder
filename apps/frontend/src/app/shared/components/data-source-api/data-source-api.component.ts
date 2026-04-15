import { Component, effect, input, output, signal } from '@angular/core'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirAxes } from '@ng-icons/iconoir'
import {
  ButtonComponent,
  DatasetServiceDistribution,
  OnlineServiceResourceInputComponent
} from 'geonetwork-ui'

export interface ApiData {
  serviceUrl: string
  layerName: string
  serviceProtocol: string
}

const EMPTY_SERVICE: DatasetServiceDistribution = {
  type: 'service',
  url: null as unknown as URL,
  accessServiceProtocol: 'ogcFeatures'
}

@Component({
  selector: 'app-data-source-api',
  imports: [NgIconComponent, ButtonComponent, OnlineServiceResourceInputComponent],
  templateUrl: './data-source-api.component.html',
  providers: [
    provideIcons({ iconoirAxes }),
    provideNgIconsConfig({ size: '2em' })
  ]
})
export class DataSourceApiComponent {
  initialValue = input<ApiData | null>(null)
  apiDataChanged = output<ApiData | null>()

  currentService = signal<DatasetServiceDistribution>({ ...EMPTY_SERVICE })
  selectedLayer = signal<ApiData | null>(null)

  constructor() {
    effect(() => {
      const init = this.initialValue()
      if (init) {
        this.selectedLayer.set(init)
        this.currentService.set({
          type: 'service',
          url: new URL(init.serviceUrl),
          accessServiceProtocol:
            (init.serviceProtocol as DatasetServiceDistribution['accessServiceProtocol']) ??
            'ogcFeatures',
          identifierInService: init.layerName
        })
      }
    })
  }

  get protocolLabel(): string {
    const protocol = this.selectedLayer()?.serviceProtocol
    return !protocol || protocol === 'wfs' ? 'WFS' : 'OGC API'
  }

  handleServiceChange(service: DatasetServiceDistribution): void {
    const layerName = service.identifierInService ?? service.name ?? null
    const serviceUrl = service.url?.toString() ?? null
    const serviceProtocol = service.accessServiceProtocol ?? null
    if (layerName && serviceUrl) {
      const data: ApiData = {
        serviceUrl,
        layerName,
        serviceProtocol: serviceProtocol ?? 'ogcFeatures'
      }
      this.selectedLayer.set(data)
      this.currentService.set(service)
      this.apiDataChanged.emit(data)
    }
  }

  removeService(): void {
    this.selectedLayer.set(null)
    this.currentService.set({ ...EMPTY_SERVICE })
    this.apiDataChanged.emit(null)
  }
}
