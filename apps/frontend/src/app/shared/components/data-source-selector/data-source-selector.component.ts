import { Component, effect, inject, input, output } from '@angular/core'
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatRadioModule } from '@angular/material/radio'
import {
  NgIconComponent,
  provideIcons,
  provideNgIconsConfig
} from '@ng-icons/core'
import { iconoirAttachment } from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import { ButtonComponent, CheckToggleComponent, FileInputComponent, TextInputComponent } from 'geonetwork-ui'

export interface SourceData {
  type: 'url'
  url: string
  authEnabled: boolean
  username: string
  password: string
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

  sourceData = input<SourceData>({
    type: 'url',
    url: '',
    authEnabled: false,
    username: '',
    password: ''
  })
  sourceChanged = output<SourceData>()

  form = this.fb.group({
    sourceType: this.fb.control<'url'>('url', { nonNullable: true }),
    url: this.fb.control('', {
      nonNullable: true,
      validators: [Validators.required, Validators.pattern(/^https?:\/\/.+/)]
    }),
    authEnabled: this.fb.control(false, { nonNullable: true }),
    username: this.fb.control('', { nonNullable: true }),
    password: this.fb.control('', { nonNullable: true })
  })

  constructor() {
    // Sync input to form
    effect(() => {
      const data = this.sourceData()
      this.form.patchValue(data, { emitEvent: false })
    })

    // Emit form changes
    this.form.valueChanges.subscribe((value) => {
      this.sourceChanged.emit({
        type: value.sourceType!,
        url: value.url!,
        authEnabled: value.authEnabled!,
        username: value.username!,
        password: value.password!
      })
    })
  }

  handleFileChange(file: globalThis.File | null): void {
    console.log('File selected:', file)
  }

  handleUrlChange(url: string): void {
    this.form.controls.url.setValue(url)
  }

  removeItem(): void {
    this.form.controls.url.setValue('')
  }
}
