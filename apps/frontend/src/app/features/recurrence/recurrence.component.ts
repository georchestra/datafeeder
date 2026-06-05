import { Component, OnInit, inject, signal } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import { ConfirmationDialogComponent } from 'geonetwork-ui'
import { firstValueFrom } from 'rxjs'
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
  private matDialog = inject(MatDialog)
  private translate = inject(TranslateService)

  intlink_id = this.store.intlinkId()
  recurrencePresets = signal<RecurrencePresetItem[]>([])
  readonly selectedPresetId: ReturnType<typeof signal<RecurrencePreset | null>>

  constructor() {
    const link = this.store.integrityLink()
    this.selectedPresetId = signal<RecurrencePreset | null>(
      link?.schedule_enabled ? link.preset_id ?? null : null
    )
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

  async onPresetChange(presetId: RecurrencePreset | null): Promise<void> {
    const previous = this.selectedPresetId()
    this.selectedPresetId.set(presetId)
    if (presetId === 'EVERY_MINUTE') {
      const dialogRef = this.matDialog.open(ConfirmationDialogComponent, {
        data: {
          title: this.translate.instant('recurrence.everyMinuteWarningTitle'),
          message: this.translate.instant('recurrence.everyMinuteWarning'),
          confirmText: this.translate.instant('common.continue'),
          cancelText: this.translate.instant('common.cancel'),
          focusCancel: 'cancel'
        }
      })
      const confirmed = await firstValueFrom(dialogRef.afterClosed())
      if (!confirmed) {
        this.selectedPresetId.set(previous)
        return
      }
    }
    await this.saveSchedule(presetId)
  }

  private async saveSchedule(presetId: RecurrencePreset | null): Promise<void> {
    if (!this.intlink_id) return
    try {
      const updatedLink = await this.api.invoke(
        updateScheduleIngestionIntegrityLinkIntegrityLinkIdSchedulePatch,
        {
          integrity_link_id: this.intlink_id,
          body: { preset: presetId }
        }
      )
      this.store.integrityLink.update((current) => ({
        ...current!,
        preset_id: updatedLink.preset_id,
        schedule: updatedLink.schedule,
        schedule_enabled: updatedLink.schedule_enabled
      }))
    } catch (err) {
      console.error('Failed to update schedule:', err)
      this.operationToastStore.addError('updateSchedule')
    }
  }
}
