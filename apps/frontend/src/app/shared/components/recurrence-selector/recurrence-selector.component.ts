import 'cronstrue/locales/de'
import 'cronstrue/locales/es'
import 'cronstrue/locales/fr'
import 'cronstrue/locales/it'
import 'cronstrue/locales/nl'
import 'cronstrue/locales/pt_BR'
import cronstrue from 'cronstrue/i18n'
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output
} from '@angular/core'
import { toSignal } from '@angular/core/rxjs-interop'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatSelectModule } from '@angular/material/select'
import { MatTooltipModule } from '@angular/material/tooltip'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { map } from 'rxjs'
import { RecurrencePresetItem } from '../../../core/api/models/recurrence-preset-item'
import { RecurrencePreset } from '../../../core/api/models'

const CUSTOM_CRON_VALUE = '__custom__'

type Recurrence = {
  cron: string
  preset_id: RecurrencePreset | null
}

@Component({
  selector: 'app-recurrence-selector',
  standalone: true,
  imports: [
    TranslatePipe,
    MatFormFieldModule,
    MatSelectModule,
    MatTooltipModule
  ],
  templateUrl: './recurrence-selector.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RecurrenceSelectorComponent {
  private translate = inject(TranslateService)

  private currentLang = toSignal(
    this.translate.onLangChange.pipe(map((e) => e.lang)),
    { initialValue: this.translate.currentLang ?? 'en' }
  )

  readonly customCronValue = CUSTOM_CRON_VALUE

  /** Available recurrence presets from GET /ingestion/recurrence-presets */
  presets = input<RecurrencePresetItem[]>([])

  /** Current recurrence from IntegrityLinkResponse (for read-only display) */
  currentRecurrence = input<Recurrence | null>(null)

  /** Currently selected preset ID (for wizard write mode) */
  selectedPresetId = input<string | null>(null)

  /** When true, renders as a non-interactive read-only combobox */
  disabled = input<boolean>(false)

  /** Emits the chosen preset ID, or null when the user clears the selection */
  presetChange = output<string | null>()

  /** Human-readable label for the current recurrence (used in disabled mode) */
  displayLabel = computed<string>(() => {
    const lang = this.currentLang()
    const r = this.currentRecurrence()
    if (!r || (!r.preset_id && !r.cron)) {
      return this.translate.instant('recurrence.none')
    }
    if (r.preset_id) {
      return this.translate.instant(`recurrence.preset.${r.preset_id}`)
    }
    try {
      const locale = lang.substring(0, 2)
      return cronstrue.toString(r.cron!, {
        locale,
        throwExceptionOnParseError: false
      })
    } catch {
      return r.cron!
    }
  })

  /** The value bound to mat-select */
  selectValue = computed<string>(() => {
    if (this.disabled()) {
      const r = this.currentRecurrence()
      if (!r || (!r.preset_id && !r.cron)) return ''
      return r.preset_id ?? CUSTOM_CRON_VALUE
    }
    return this.selectedPresetId() ?? ''
  })

  /** Tooltip text showing the full label of the currently selected option */
  tooltipLabel = computed<string>(() => {
    const value = this.selectValue()

    if (!value) return this.translate.instant('recurrence.none')
    if (value === CUSTOM_CRON_VALUE) return this.displayLabel()

    const preset = this.presets().find((p) => p.id === value)
    if (preset) return this.translate.instant(`recurrence.preset.${preset.id}`)
    return this.displayLabel()
  })

  /** True when disabled and showing a custom (non-preset) cron */
  isCustomCron = computed<boolean>(() => {
    const r = this.currentRecurrence()
    return this.disabled() && !!r?.cron && !r?.preset_id
  })

  /** True when disabled with a preset that is absent from the presets list */
  shouldShowPresetFallback = computed<boolean>(() => {
    const presetId = this.currentRecurrence()?.preset_id
    return (
      this.disabled() &&
      !!presetId &&
      !this.presets().some((p) => p.id === presetId)
    )
  })
}
