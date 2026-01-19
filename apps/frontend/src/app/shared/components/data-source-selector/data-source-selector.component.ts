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

marker('input.file.selectFileLabel')
marker('input.file.dropFileLabel')
marker('input.file.orInputUrl')

export interface SourceData {
  type: 'url' | 'file'
  file?: globalThis.File
  url?: string
  authEnabled: boolean
  username?: string
  password?: string
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
    FileInputComponent
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
    radio: this.fb.control<'file'>('file'),
    source: this.fb.group({
      type: this.fb.control<'file' | 'url'>('file'),
      file: this.fb.control<globalThis.File | null>(null),
      url: this.fb.control<string | null>(null),
      authEnabled: this.fb.control<boolean>(false, { nonNullable: true }),
      username: this.fb.control<string | null>(null),
      password: this.fb.control<string | null>(null)
    })
  })

  constructor() {
    // Emit form changes
    this.form.controls.source.valueChanges.subscribe((value) => {
      this.sourceChanged.emit({
        type: value.type,
        file: value.file,
        url: value.url,
        authEnabled: value.authEnabled,
        username: value.username,
        password: value.password
      })
    })
  }

  handleFileChange(file: globalThis.File | null): void {
    this.form.controls.source.setValue({
      type: 'file',
      file: file,
      url: null,
      authEnabled: false,
      username: null,
      password: null
    })
  }

  handleUrlChange(url: string): void {
    this.form.controls.source.patchValue({
      type: 'url',
      file: null,
      url: url
    })
  }

  removeItem(): void {
    this.form.controls.source.setValue({
      type: 'file',
      file: null,
      url: null,
      authEnabled: false,
      username: null,
      password: null
    })
  }
}
