import {
  Component,
  input,
  effect,
  inject,
  output,
  ChangeDetectionStrategy,
  signal,
  computed
} from '@angular/core'
import { ReactiveFormsModule } from '@angular/forms'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatInputModule } from '@angular/material/input'
import { MatTableModule } from '@angular/material/table'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import type {
  StagingMetadataResponse,
  StagingPreviewResponse
} from '../../../core/api/models'
import {
  DropdownSelectorComponent,
  ButtonComponent,
  SpinningLoaderComponent,
  DropdownChoice
} from 'geonetwork-ui'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirDataTransferBoth } from '@ng-icons/iconoir'
import { AlertBoxComponent } from '../alert-box/alert-box.component'

@Component({
  selector: 'app-dataset-configuration',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    TranslatePipe,
    NgIconComponent,
    DropdownSelectorComponent,
    ButtonComponent,
    AlertBoxComponent,
    SpinningLoaderComponent
  ],
  templateUrl: './dataset-configuration.component.html',
  styleUrls: ['./dataset-configuration.component.scss'],
  providers: [
    provideIcons({
      iconoirDataTransferBoth
    }),
    provideNgIconsConfig({
      size: '2em'
    })
  ]
})
export class DatasetConfigurationComponent {
  private translate = inject(TranslateService)

  metadata = input<StagingMetadataResponse | null>(null)
  preview = input<StagingPreviewResponse | null>(null)
  previewError = input<string | null>(null)
  previewLoading = input<boolean>(false)

  configChanged = output<{
    projection: string
    colX: string
    colY: string
  }>()

  selectedProjection = signal<string>('')
  selectedXCol = signal<string>('')
  selectedYCol = signal<string>('')
  showError = signal<boolean>(false)

  errorTitle = computed(() => this.translate.instant('import.dataSource.error'))

  constructor() {
    // Initialize selected values from metadata when it loads
    effect(() => {
      const meta = this.metadata()
      if (meta) {
        this.selectedProjection.set(meta.force_projection?.type || '')
        this.selectedXCol.set(meta.force_projection?.x_column || '')
        this.selectedYCol.set(meta.force_projection?.y_column || '')
      }
    })

    effect(() => this.showError.set(!!this.previewError()))
  }

  displayedColumns = computed(() => {
    const meta = this.metadata()
    return meta?.columns.map((col) => col.name) || []
  })

  dataSource = computed(() => {
    const data = this.preview()?.data || []
    return data
  })

  projections: DropdownChoice[] = [
    { value: '-1', label: '-' }, // keep -1 because gn-ui does not select ''...
    { value: 'EPSG:4326', label: 'WGS 84' },
    { value: 'EPSG:3857', label: 'Web Mercator' }
    // TODO: Add more projections as needed, from config
  ]

  columns = computed<DropdownChoice[]>(() => {
    const meta = this.metadata()
    if (!meta?.columns) {
      return [{ value: '', label: '-' }]
    }
    return [
      { value: '', label: '-' },
      ...meta.columns.map((col) => ({
        value: col.name,
        label: col.name
      }))
    ]
  })

  private emitConfigChanged() {
    const projection = this.selectedProjection()
    const colX = this.selectedXCol()
    const colY = this.selectedYCol()

    this.configChanged.emit({
      projection,
      colX,
      colY
    })
  }

  onSwitchXY() {
    const currentLat = this.selectedXCol()
    const currentLong = this.selectedYCol()

    this.selectedXCol.set(currentLong)
    this.selectedYCol.set(currentLat)

    this.emitConfigChanged()
  }

  selectYCol(col: string) {
    this.selectedYCol.set(col)
    this.emitConfigChanged()
  }

  selectXCol(col: string) {
    this.selectedXCol.set(col)
    this.emitConfigChanged()
  }

  selectProjection(projection: string) {
    this.selectedProjection.set(projection)
    this.emitConfigChanged()
  }
}
