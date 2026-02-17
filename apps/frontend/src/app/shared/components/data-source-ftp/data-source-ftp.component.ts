import { Component, inject, output } from '@angular/core'
import { FormBuilder, ReactiveFormsModule } from '@angular/forms'
import { TranslatePipe } from '@ngx-translate/core'
import { TextInputComponent } from 'geonetwork-ui'

export interface FTPData {
  host: string
  port: number
  username: string
  password: string
  path: string
}

@Component({
  selector: 'app-data-source-ftp',
  imports: [ReactiveFormsModule, TranslatePipe, TextInputComponent],
  templateUrl: './data-source-ftp.component.html',
  styleUrls: ['./data-source-ftp.component.scss']
})
export class DataSourceFtpComponent {
  private fb = inject(FormBuilder)

  ftpDataChanged = output<FTPData>()

  form = this.fb.group({
    host: this.fb.control<string>(''),
    port: this.fb.control<number>(21),
    username: this.fb.control<string>(''),
    password: this.fb.control<string>(''),
    path: this.fb.control<string>('')
  })

  constructor() {
    this.form.valueChanges.subscribe((value) => {
      this.ftpDataChanged.emit({
        host: value.host || '',
        port: value.port || 21,
        username: value.username || '',
        password: value.password || '',
        path: value.path || ''
      })
    })
  }
}
