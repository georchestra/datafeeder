import 'cronstrue/locales/de'
import 'cronstrue/locales/es'
import 'cronstrue/locales/fr'
import 'cronstrue/locales/it'
import 'cronstrue/locales/nl'
import 'cronstrue/locales/pt_BR'
import cronstrue from 'cronstrue/i18n'
import { inject, Pipe, PipeTransform } from '@angular/core'
import { TranslateService } from '@ngx-translate/core'
import { RecurrencePreset } from '../../core/api/models'

@Pipe({ name: 'recurrenceLabel', standalone: true, pure: false })
export class RecurrenceLabelPipe implements PipeTransform {
  private translate = inject(TranslateService)

  transform(
    schedule: string | null,
    presetId?: RecurrencePreset | null
  ): string | null {
    if (!schedule) return null
    if (presetId) {
      return this.translate.instant(`recurrence.preset.${presetId}`)
    }
    try {
      const locale = this.translate.currentLang?.substring(0, 2) ?? 'en'
      return cronstrue.toString(schedule, {
        locale,
        throwExceptionOnParseError: false
      })
    } catch {
      return schedule
    }
  }
}
