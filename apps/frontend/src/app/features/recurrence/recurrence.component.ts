import {
  Component,
  OnInit,
  effect,
  inject,
  signal,
  untracked
} from '@angular/core'
import { TranslatePipe } from '@ngx-translate/core'
import { Api } from '../../core/api/api'
import { RecurrencePreset } from '../../core/api/models/recurrence-preset'
import { RecurrencePresetItem } from '../../core/api/models'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
import { RecurrenceSelectorComponent } from '../../shared/components/recurrence-selector/recurrence-selector.component'
import {
  listRecurrencePresetsIngestionRecurrencePresetsGet,
  updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch
} from '../../core/api/functions'

@Component({
  selector: 'app-recurrence',
  imports: [RecurrenceSelectorComponent, TranslatePipe],
  templateUrl: './recurrence.component.html',
  styleUrl: './recurrence.component.css'
})
export class RecurrenceComponent implements OnInit {
  private api = inject(Api)
  readonly store = inject(IntegrityLinkStore)
  private operationToastStore = inject(OperationToastStore)

  intlink_id = this.store.intlinkId()
  recurrencePresets = signal<RecurrencePresetItem[]>([])
  readonly selectedPresetId: ReturnType<typeof signal<RecurrencePreset | null>>

  constructor() {
    const link = this.store.integrityLink()
    this.selectedPresetId = signal<RecurrencePreset | null>(
      link?.schedule_enabled ? link.preset_id ?? null : null
    )

    let initialized = false
    effect(() => {
      const presetId = this.selectedPresetId()
      if (!initialized) {
        initialized = true
        return
      }
      const intlinkId = untracked(() => this.intlink_id)
      if (!intlinkId) return
      this.api
        .invoke(
          updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
          {
            integrity_link_id: intlinkId,
            body: { preset: presetId }
          }
        )
        .then((updatedLink) => {
          this.store.integrityLink.update((current) => ({
            ...current!,
            preset_id: updatedLink.preset_id,
            schedule: updatedLink.schedule,
            schedule_enabled: updatedLink.schedule_enabled
          }))
        })
        .catch((err) => {
          console.error('Failed to update schedule:', err)
          this.operationToastStore.addError('updateSchedule')
        })
    })
  }

  ngOnInit(): void {
    this.api
      .invoke(listRecurrencePresetsIngestionRecurrencePresetsGet, {})
      .then((presets) => this.recurrencePresets.set(presets))
      .catch((err) => {
        console.error('Failed to load recurrence presets:', err)
        this.operationToastStore.addError('loadPresets')
      })
  }
}
