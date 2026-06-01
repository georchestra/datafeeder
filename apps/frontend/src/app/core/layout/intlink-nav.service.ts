import { computed, inject, Injectable } from '@angular/core'
import { Router } from '@angular/router'
import { TranslateService } from '@ngx-translate/core'
import { MatDialog } from '@angular/material/dialog'
import { firstValueFrom } from 'rxjs'
import { ConfirmationDialogComponent } from 'geonetwork-ui'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import { SettingsService } from '../settings/settings.service'
import { Api } from '../api/api'
import {
  deleteIntegrityLinkScheduleIngestionIntegrityLinkIntegrityLinkIdScheduleDelete,
  getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet
} from '../api/functions'

export type IntlinkRoute = 'edit' | 'recurrence' | 'events' | 'authorizations'

@Injectable({ providedIn: 'root' })
export class IntlinkNavService {
  private store = inject(IntegrityLinkStore)
  private settingsService = inject(SettingsService)
  private api = inject(Api)
  private matDialog = inject(MatDialog)
  private translate = inject(TranslateService)
  private readonly router = inject(Router)

  readonly accessibleRoutes = computed((): IntlinkRoute[] => {
    const routes: IntlinkRoute[] = ['edit']
    if (this.store.isRemoteDataset() && this.store.isOwnerOrAdmin())
      routes.push('recurrence')
    if (this.store.isOwnerOrAdmin()) routes.push('authorizations')
    return routes
  })

  prevRoute(current: IntlinkRoute): IntlinkRoute | null {
    const routes = this.accessibleRoutes()
    const idx = routes.indexOf(current)
    return idx > 0 ? routes[idx - 1] : null
  }

  nextRoute(current: IntlinkRoute): Exclude<IntlinkRoute, 'edit'> | null {
    const routes = this.accessibleRoutes()
    const idx = routes.indexOf(current)
    return idx >= 0 && idx < routes.length - 1
      ? (routes[idx + 1] as Exclude<IntlinkRoute, 'edit'>)
      : null
  }

  catalogueUrl(metadataId: string | null | undefined): string | null {
    const tpl = this.settingsService.getSetting<string>('catalogue_url')
    if (!tpl || !metadataId) return null
    return tpl.replace('{metadata_id}', metadataId)
  }

  navigate(intlinkId: string, route: IntlinkRoute): Promise<boolean> {
    return this.router.navigate(['/', intlinkId, route])
  }

  /** i18n key for the "next" button label when navigating to a given intlink route */
  nextRouteLabel(route: Exclude<IntlinkRoute, 'edit'>): string {
    switch (route) {
      case 'recurrence':
        return 'footer.next.recurrence'
      case 'events':
        return 'footer.next.events'
      case 'authorizations':
        return 'footer.next.authorizations'
    }
  }

  async reconfigure(): Promise<void> {
    const intlink = this.store.integrityLink()
    const intlinkId = this.store.intlinkId()
    if (!intlink || !intlinkId) return

    if (intlink.schedule_enabled) {
      const runs = await this.api.invoke(
        getDagRunByIntlinkAirflowDagsDagIdRunsIntlinkIdGet,
        { dag_id: 'process_dag', intlink_id: intlinkId }
      )
      const hasActiveRun = runs.dag_runs.some(
        (r) => r.state === 'running' || r.state === 'queued'
      )
      const messageKey = hasActiveRun
        ? 'sidebar.reconfigureDataset.warningActiveRun'
        : 'sidebar.reconfigureDataset.warning'

      const dialogRef = this.matDialog.open(ConfirmationDialogComponent, {
        data: {
          title: this.translate.instant(
            'sidebar.reconfigureDataset.warningTitle'
          ),
          message: this.translate.instant(messageKey),
          confirmText: this.translate.instant('common.continue'),
          cancelText: this.translate.instant('common.cancel'),
          focusCancel: 'cancel'
        }
      })
      const confirmed = await firstValueFrom(dialogRef.afterClosed())
      if (!confirmed) return

      await this.api.invoke(
        deleteIntegrityLinkScheduleIngestionIntegrityLinkIntegrityLinkIdScheduleDelete,
        { integrity_link_id: intlinkId }
      )
    }

    this.router.navigate(['/import', intlinkId])
  }
}
