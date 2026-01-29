import {
  Component,
  input,
  effect,
  inject,
  output,
  ChangeDetectionStrategy
} from '@angular/core'
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatInputModule } from '@angular/material/input'
import { MatTableModule } from '@angular/material/table'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import type { StagingMetadataResponse } from '../../../core/api/models'

@Component({
  selector: 'app-dataset-title',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    TranslatePipe
  ],
  templateUrl: './dataset-title.component.html',
  styleUrls: ['./dataset-title.component.scss']
})
export class DatasetTitleComponent {
  private fb = inject(FormBuilder)
  private translate = inject(TranslateService)

  validated = output<string>()

  form = this.fb.group({
    title: this.fb.control('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(100)
      ]
    })
  })

  metadata = input<StagingMetadataResponse | undefined>()

  constructor() {
    // Sync metadata title to form when loaded
    effect(() => {
      const meta = this.metadata()
      if (meta) {
        const title =
          meta.title ||
          this.translate.instant('import.datasetConfiguration.untitled')
        this.form.patchValue({ title }, { emitEvent: false })
      }
    })
  }

  submitForm() {
    if (this.form.valid) {
      this.validated.emit(this.form.value.title!)
    } else {
      this.form.markAllAsTouched()
    }
  }
}
