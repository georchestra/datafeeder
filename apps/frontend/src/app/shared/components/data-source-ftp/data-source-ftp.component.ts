import { Component, output, signal } from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { TextInputComponent } from 'geonetwork-ui'
import { UiInputPasswordComponent } from '../ui-input-password/ui-input-password.component'

export interface FTPData {
  host: string
  port: number
  username: string
  password: string
  path: string
}

@Component({
  selector: 'app-data-source-ftp',
  imports: [TranslatePipe, TextInputComponent, UiInputPasswordComponent],
  templateUrl: './data-source-ftp.component.html'
})
export class DataSourceFtpComponent {
  ftpDataChanged = output<FTPData>()

  formData = signal<FTPData>({
    host: '',
    port: 21,
    username: '',
    password: '',
    path: ''
  })

  set<K extends keyof FTPData>(key: K, value: FTPData[K]): void {
    this.formData.update((d) => ({ ...d, [key]: value }))
    this.ftpDataChanged.emit({
      ...this.formData(),
      port: this.formData().port || 21
    })
  }
}
