import { Component, effect, inject, input, output, signal } from '@angular/core'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { MatRadioModule } from '@angular/material/radio'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirAttachment, iconoirAxes } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  CheckToggleComponent,
  DatasetServiceDistribution,
  FileInputComponent,
  OnlineServiceResourceInputComponent,
  TextInputComponent
} from 'geonetwork-ui'
import {
  DataSourceFtpComponent,
  type FTPData
} from '../data-source-ftp/data-source-ftp.component'
import { UiInputPasswordComponent } from '../ui-input-password/ui-input-password.component'

marker('input.file.selectFileLabel')
marker('input.file.dropFileLabel')
marker('input.file.orInputUrl')
marker('import.dataSource.chooseType.ftp')
marker('import.dataSource.ftp.host')
marker('import.dataSource.ftp.port')
marker('import.dataSource.ftp.username')
marker('import.dataSource.ftp.password')
marker('import.dataSource.ftp.path')
marker('import.dataSource.chooseType.database')
marker('import.dataSource.database.schema')
marker('import.dataSource.database.table')
marker('import.dataSource.chooseType.api')

export type SourceType = 'url' | 'file' | 'ftp' | 'database' | 'api'
export type RadioType = 'file' | 'ftp' | 'database' | 'api'

export interface SourceData {
  type: SourceType
  file?: globalThis.File
  url?: string
  authEnabled: boolean
  username?: string
  password?: string
  ftpHost?: string
  ftpPort?: number
  ftpPath?: string
  dbSchema?: string
  dbTable?: string
  serviceUrl?: string
  layerName?: string
  serviceProtocol?: string
}

const EMPTY_SERVICE: DatasetServiceDistribution = {
  type: 'service',
  url: null as unknown as URL,
  accessServiceProtocol: 'wfs'
}

@Component({
  selector: 'app-data-source-selector',
  imports: [
    ReactiveFormsModule,
    MatRadioModule,
    TranslatePipe,
    NgIconComponent,
    TranslatePipe,
    ButtonComponent,
    CheckToggleComponent,
    TextInputComponent,
    FileInputComponent,
    DataSourceFtpComponent,
    UiInputPasswordComponent,
    OnlineServiceResourceInputComponent
  ],
  templateUrl: './data-source-selector.component.html',
  providers: [
    provideIcons({
      iconoirAttachment,
      iconoirAxes
    }),
    provideNgIconsConfig({
      size: '2em'
    })
  ]
})
export class DataSourceSelectorComponent {
  private fb = inject(FormBuilder)

  databaseSourceEnabled = input<boolean>(false)
  initialDatabaseSource = input<{ schema: string; table: string } | null>(null)
  initialApiSource = input<{
    url: string
    layerName: string
    protocol: string
  } | null>(null)

  sourceChanged = output<SourceData>()

  currentService = signal<DatasetServiceDistribution>({ ...EMPTY_SERVICE })

  form = this.fb.group({
    radio: this.fb.control<RadioType>('file'),
    source: this.fb.group({
      type: this.fb.control<SourceType>('file'),
      file: this.fb.control<globalThis.File | null>(null),
      url: this.fb.control<string | null>(null),
      authEnabled: this.fb.control<boolean>(false, { nonNullable: true }),
      username: this.fb.control<string | null>(null),
      password: this.fb.control<string | null>(null),
      ftpHost: this.fb.control<string | null>(null),
      ftpPort: this.fb.control<number | null>(null),
      ftpPath: this.fb.control<string | null>(null),
      dbSchema: this.fb.control<string | null>(null),
      dbTable: this.fb.control<string | null>(null),
      serviceUrl: this.fb.control<string | null>(null),
      layerName: this.fb.control<string | null>(null),
      serviceProtocol: this.fb.control<string | null>(null)
    })
  })

  constructor() {
    effect(() => {
      const dbSource = this.initialDatabaseSource()
      if (dbSource && !this.form.dirty) {
        this.form.controls.radio.setValue('database')
        this.form.controls.source.patchValue({
          type: 'database',
          dbSchema: dbSource.schema,
          dbTable: dbSource.table
        })
      }
    })

    effect(() => {
      const apiSource = this.initialApiSource()
      if (apiSource && !this.form.dirty) {
        this.form.controls.radio.setValue('api')
        this.form.controls.source.patchValue({
          type: 'api',
          serviceUrl: apiSource.url,
          layerName: apiSource.layerName,
          serviceProtocol: apiSource.protocol
        })
        this.currentService.set({
          type: 'service',
          url: new URL(apiSource.url),
          accessServiceProtocol:
            (apiSource.protocol as DatasetServiceDistribution['accessServiceProtocol']) ??
            'wfs',
          identifierInService: apiSource.layerName
        })
      }
    })

    this.form.controls.source.valueChanges.subscribe((value) => {
      this.sourceChanged.emit({
        type: value.type,
        file: value.file,
        url: value.url,
        authEnabled: value.authEnabled,
        username: value.username,
        password: value.password,
        ftpHost: value.ftpHost,
        ftpPort: value.ftpPort,
        ftpPath: value.ftpPath,
        dbSchema: value.dbSchema,
        dbTable: value.dbTable,
        serviceUrl: value.serviceUrl,
        layerName: value.layerName,
        serviceProtocol: value.serviceProtocol
      })
    })
  }

  handleFileChange(file: globalThis.File | null): void {
    this.form.controls.source.patchValue({ type: 'file', file, url: null })
  }

  handleUrlChange(url: string): void {
    this.form.controls.source.patchValue({ type: 'url', url, file: null })
  }

  resetSource(): void {
    this.form.controls.source.setValue({
      type: 'file',
      file: null,
      url: null,
      authEnabled: false,
      username: null,
      password: null,
      ftpHost: null,
      ftpPort: null,
      ftpPath: null,
      dbSchema: null,
      dbTable: null,
      serviceUrl: null,
      layerName: null,
      serviceProtocol: null
    })
    this.currentService.set({ ...EMPTY_SERVICE })
  }

  removeItem(): void {
    this.form.controls.radio.setValue('file')
    this.resetSource()
  }

  handleRadioChange(type: RadioType): void {
    this.resetSource()
    this.form.controls.source.patchValue({ type })
  }

  handleFtpDataChange(data: FTPData): void {
    this.form.controls.source.patchValue({
      ftpHost: data.host,
      ftpPort: data.port,
      username: data.username,
      password: data.password,
      ftpPath: data.path
    })
  }

  removeService(): void {
    this.currentService.set({ ...EMPTY_SERVICE })
    this.form.controls.source.patchValue({
      serviceUrl: null,
      layerName: null,
      serviceProtocol: null
    })
  }

  get protocolLabel(): string {
    const protocol = this.form.controls.source.controls.serviceProtocol.value
    return !protocol || protocol === 'wfs' ? 'WFS' : 'OGC API'
  }

  handleServiceChange(service: DatasetServiceDistribution): void {
    this.currentService.set(service)
    this.form.controls.source.patchValue({
      serviceUrl: service.url?.toString() ?? null,
      layerName: service.identifierInService ?? service.name ?? null,
      serviceProtocol: service.accessServiceProtocol ?? null
    })
  }
}
