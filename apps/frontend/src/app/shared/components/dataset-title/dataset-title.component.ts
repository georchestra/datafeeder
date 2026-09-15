import {
  Component,
  input,
  effect,
  inject,
  output,
  viewChild,
  ElementRef,
  ChangeDetectionStrategy
} from '@angular/core'
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatInputModule } from '@angular/material/input'
import { MatTableModule } from '@angular/material/table'
import { TranslatePipe } from '@ngx-translate/core'
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

  validated = output<string>()
  titleChanged = output<string>()

  metadata = input<StagingMetadataResponse | undefined>()
  isReconfiguring = input<boolean>(false)

  private titleInput = viewChild<ElementRef<HTMLInputElement>>('titleInput')

  form = this.fb.group({
    title: this.fb.control('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(255)
      ]
    })
  })

  constructor() {
    // When reconfiguring, show the persisted title in the (disabled) field.
    // For a new ingestion, leave the field empty instead of pre-filling it
    // with the backend's filename-derived default.
    effect(() => {
      const meta = this.metadata()
      if (meta && this.isReconfiguring()) {
        const title = meta.title ?? ''
        this.form.patchValue({ title }, { emitEvent: false })
      }
    })

    // Disable/enable title control based on has_final_table
    effect(() => {
      const isDisabled = this.isReconfiguring()
      const titleControl = this.form.controls.title
      if (isDisabled) {
        titleControl.disable({ emitEvent: false })
      } else {
        titleControl.enable({ emitEvent: false })
      }
    })

    // Propagate user edits back to parent
    this.form.controls.title.valueChanges.subscribe((value) => {
      this.titleChanged.emit(value)
    })

    // Focus the title input once it renders. Using the native `autofocus`
    // attribute instead races with Angular Material's FocusMonitor setup
    // and spuriously marks the control as touched before the user interacts.
    effect(() => {
      this.titleInput()?.nativeElement.focus()
    })
  }

  submitForm() {
    // !!! If input is disabled, angular considers form is invalid
    const titleControl = this.form.controls.title

    if (
      (titleControl.disabled && this.metadata()?.title) ||
      titleControl.valid
    ) {
      this.validated.emit(this.form.value.title!)
    } else {
      this.form.markAllAsTouched()
    }
  }
}
