import { Component, inject, output } from '@angular/core'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { MatRadioModule } from '@angular/material/radio'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirAttachment } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  CheckToggleComponent,
  FileInputComponent,
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

export interface SourceData {
  type: 'url' | 'file' | 'ftp'
  file?: globalThis.File
  url?: string
  authEnabled: boolean
  username?: string
  password?: string
  ftpHost?: string
  ftpPort?: number
  ftpPath?: string
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
    UiInputPasswordComponent
  ],
  templateUrl: './data-source-selector.component.html',
  providers: [
    provideIcons({
      iconoirAttachment
    }),
    provideNgIconsConfig({
      size: '2em'
    })
  ]
})
export class DataSourceSelectorComponent {
  private fb = inject(FormBuilder)

  sourceChanged = output<SourceData>()

  form = this.fb.group({
    radio: this.fb.control<'file' | 'ftp'>('file'),
    source: this.fb.group({
      type: this.fb.control<'file' | 'url' | 'ftp'>('file'),
      file: this.fb.control<globalThis.File | null>(null),
      url: this.fb.control<string | null>(null),
      authEnabled: this.fb.control<boolean>(false, { nonNullable: true }),
      username: this.fb.control<string | null>(null),
      password: this.fb.control<string | null>(null),
      ftpHost: this.fb.control<string | null>(null),
      ftpPort: this.fb.control<number | null>(null),
      ftpPath: this.fb.control<string | null>(null)
    })
  })

  constructor() {
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
        ftpPath: value.ftpPath
      })
    })
  }

  handleFileChange(file: globalThis.File | null): void {
    this.form.controls.source.patchValue({ file })
  }

  handleUrlChange(url: string): void {
    this.form.controls.source.patchValue({
      type: 'url',
      url
    })
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
      ftpPath: null
    })
  }

  removeItem(): void {
    this.form.controls.radio.setValue('file')
    this.resetSource()
  }

  handleRadioChange(type: 'file' | 'ftp'): void {
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
}
