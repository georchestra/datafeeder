import {
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
  TemplateRef,
  untracked,
  viewChild
} from '@angular/core'
import {
  ActivatedRoute,
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirFloppyDisk,
  iconoirRefreshCircle,
  iconoirOpenNewWindow,
  iconoirHome,
  iconoirJournalPage,
  iconoirListSelect,
  iconoirCalendarRotate,
  iconoirShieldCheck
} from '@ng-icons/iconoir'
import { TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  EditorFacade,
  SpinningLoaderComponent
} from 'geonetwork-ui'
import { filter, map, startWith } from 'rxjs'
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop'
import { IntegrityLinkStore } from '../core/stores/integrity-link.store'
import { UiAlertBoxComponent } from '../shared/components/ui-alert-box/ui-alert-box.component'
import { FooterService } from '../core/layout/footer.service'
import {
  IntlinkNavService,
  type IntlinkRoute
} from '../core/layout/intlink-nav.service'
import { MetadataSaveService } from '../core/layout/metadata-save.service'

marker('intlinkLayout.error.forbidden.message')
marker('intlinkLayout.error.forbidden.title')
marker('intlinkLayout.error.not_found.message')
marker('intlinkLayout.error.not_found.title')
marker('intlinkLayout.error.server_error.message')
marker('intlinkLayout.error.server_error.title')
marker('intlinkLayout.error.unavailable_for_empty.message')
marker('intlinkLayout.error.unavailable_for_empty.title')
marker('sidebar.unavailableForEmpty')
marker('sidebar.unavailableForLocal')
marker('sidebar.recurrence')
marker('info.operation.metadataSave')
marker('sidebar.reconfigureDataset.warning')
marker('sidebar.reconfigureDataset.warningActiveRun')
marker('sidebar.reconfigureDataset.warningTitle')
marker('footer.previous')
marker('footer.previous.toEdit')
marker('footer.next.recurrence')
marker('footer.next.events')
marker('footer.next.authorizations')
marker('footer.openInCatalogue')

@Component({
  selector: 'app-intlink-layout',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    NgIconComponent,
    TranslatePipe,
    UiAlertBoxComponent,
    SpinningLoaderComponent,
    ButtonComponent
  ],
  templateUrl: './intlink-layout.component.html',
  providers: [
    provideIcons({
      iconoirFloppyDisk,
      iconoirRefreshCircle,
      iconoirOpenNewWindow,
      iconoirHome,
      iconoirJournalPage,
      iconoirListSelect,
      iconoirCalendarRotate,
      iconoirShieldCheck
    })
  ]
})
export class IntlinkLayoutComponent {
  protected readonly store = inject(IntegrityLinkStore)
  protected readonly navService = inject(IntlinkNavService)
  protected readonly metadataSaveService = inject(MetadataSaveService)
  private editor = inject(EditorFacade)

  private router = inject(Router)
  private route = inject(ActivatedRoute)
  private footerService = inject(FooterService)
  private destroyRef = inject(DestroyRef)

  protected readonly footerTpl = viewChild<TemplateRef<unknown>>('footerTpl')

  protected showUnavailableBanner = signal<boolean>(false)
  protected readonly changedSinceSave = toSignal(
    this.editor.changedSinceSave$,
    { initialValue: false }
  )

  protected readonly activeSegment = toSignal(
    this.router.events.pipe(
      filter((e) => e instanceof NavigationEnd),
      map(() => this.resolveActiveSegment()),
      startWith(this.resolveActiveSegment())
    )
  ) as ReturnType<typeof toSignal<IntlinkRoute>>

  protected readonly catalogueUrl = computed(() =>
    this.navService.catalogueUrl(this.store.integrityLink()?.metadata_id)
  )

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      if (params.get('unavailable') === '1') {
        this.showUnavailableBanner.set(true)
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { unavailable: null },
          queryParamsHandling: 'merge',
          replaceUrl: true
        })
      }
    })

    effect(() => {
      const tpl = this.footerTpl()
      const segment = this.activeSegment()
      untracked(() => {
        // Register the layout footer only for the linear-flow pages.
        // MetadataComponent handles /edit; /events is a standalone page with no footer.
        const isFlowPage =
          segment === 'recurrence' || segment === 'authorizations'
        this.footerService.setContent(isFlowPage ? tpl ?? null : null)
      })
    })

    this.destroyRef.onDestroy(() => this.footerService.setContent(null))
  }

  private resolveActiveSegment(): IntlinkRoute {
    const last = this.router.url.split('?')[0].split('/').pop()
    if (last === 'authorizations') return 'authorizations'
    if (last === 'recurrence') return 'recurrence'
    if (last === 'events') return 'events'
    return 'edit'
  }

  onSaveClick(): void {
    this.metadataSaveService.save().catch(() => undefined)
  }

  onReconfigureClick(): Promise<void> {
    return this.navService.reconfigure()
  }

  navigatePrev(): void {
    const intlinkId = this.store.intlinkId()
    const segment = this.activeSegment()
    if (!intlinkId || !segment) return
    const prev = this.navService.prevRoute(segment)
    if (prev) this.navService.navigate(intlinkId, prev)
  }

  navigateNext(): void {
    const intlinkId = this.store.intlinkId()
    const segment = this.activeSegment()
    if (!intlinkId || !segment) return
    const next = this.navService.nextRoute(segment)
    if (next) this.navService.navigate(intlinkId, next)
  }

  openCatalogue(): void {
    const url = this.catalogueUrl()
    if (url) window.open(url, '_blank', 'noopener')
  }
}
