import { inject } from '@angular/core'
import { CanDeactivateFn } from '@angular/router'
import { MatDialog } from '@angular/material/dialog'
import { TranslateService } from '@ngx-translate/core'
import { ConfirmationDialogComponent } from 'geonetwork-ui'
import { firstValueFrom } from 'rxjs'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { AiGenerationStore } from '../stores/ai-generation.store'

marker('metadata.ai.confirmLeave.title')
marker('metadata.ai.confirmLeave.message')

/**
 * Asks for confirmation before leaving a record while its AI metadata
 * generation is still running, as its result would then be discarded.
 */
export const confirmLeaveDuringAiGenerationGuard: CanDeactivateFn<
  unknown
> = async (_component, currentRoute) => {
  const aiGenerationStore = inject(AiGenerationStore)
  const generatingIntlinkId = aiGenerationStore.generatingIntlinkId()
  if (
    !generatingIntlinkId ||
    generatingIntlinkId !== currentRoute.params['intlink_id']
  )
    return true

  const translate = inject(TranslateService)
  const dialogRef = inject(MatDialog).open(ConfirmationDialogComponent, {
    data: {
      title: translate.instant('metadata.ai.confirmLeave.title'),
      message: translate.instant('metadata.ai.confirmLeave.message'),
      confirmText: translate.instant('common.continue'),
      cancelText: translate.instant('common.cancel'),
      focusCancel: 'cancel'
    }
  })
  return (await firstValueFrom(dialogRef.afterClosed())) === true
}
