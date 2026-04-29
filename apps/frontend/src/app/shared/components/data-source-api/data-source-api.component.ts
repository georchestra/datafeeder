import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
  untracked
} from '@angular/core'
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
  layerTitle?: string
  serviceProtocol: string
}

const EMPTY_SERVICE: Partial<DatasetServiceDistribution> = {
  type: 'service',
  accessServiceProtocol: 'ogcFeatures'
}

@Component({
  selector: 'app-data-source-api',
  imports: [
    NgIconComponent,
    ButtonComponent,
    OnlineServiceResourceInputComponent
  ],
  templateUrl: './data-source-api.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    provideIcons({ iconoirAxes }),
    provideNgIconsConfig({ size: '2em' })
  ]
})
export class DataSourceApiComponent {
  initialValue = input<ApiData | null>(null)
  apiDataChanged = output<ApiData | null>()

  currentService = signal<Partial<DatasetServiceDistribution>>({
    ...EMPTY_SERVICE
  })
  selectedLayer = signal<ApiData | null>(null)

  constructor() {
    effect(() => {
      const init = this.initialValue()
      if (init) {
        const prev = untracked(() => this.selectedLayer())
        const layerTitle =
          init.layerTitle ??
          (prev?.layerName === init.layerName ? prev?.layerTitle : undefined)
        this.selectedLayer.set({ ...init, layerTitle })
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

  protocolLabel = computed(() => {
    const protocol = this.selectedLayer()?.serviceProtocol
    return !protocol || protocol === 'wfs' ? 'WFS' : 'OGC API'
  })

  handleServiceChange(service: DatasetServiceDistribution): void {
    const layerName = service.identifierInService ?? service.name ?? null
    const layerTitle = service.description ?? service.name ?? undefined
    const rawUrl = service.url?.toString() ?? null
    const serviceUrl = rawUrl
      ? rawUrl.replace(/\/collections(\/.*)?$/, '')
      : null
    const serviceProtocol = service.accessServiceProtocol ?? null
    if (layerName && serviceUrl) {
      const data: ApiData = {
        serviceUrl,
        layerName,
        layerTitle,
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
