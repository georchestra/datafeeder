import { Component, computed, effect, inject, signal } from '@angular/core'
import { DatePipe } from '@angular/common'
import { Router } from '@angular/router'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { TranslatePipe, TranslateService } from '@ngx-translate/core'
import {
  Subject,
  debounceTime,
  distinctUntilChanged,
  map,
  skip,
  startWith
} from 'rxjs'
import { firstValueFrom } from 'rxjs'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { MatDialog } from '@angular/material/dialog'
import { ConfirmationDialogComponent } from 'geonetwork-ui'
import { Api } from '../../core/api/api'
import {
  deleteIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdDelete,
  listIntegrityLinksIngestionIntegrityLinksGet
} from '../../core/api/functions'
import {
  IntegrityLinkListItem,
  PublicAccess,
  RecurrencePreset
} from '../../core/api/models'
import { PUBLIC_ACCESS } from '../../core/api/models/public-access-array'
import { RECURRENCE_PRESET } from '../../core/api/models/recurrence-preset-array'
import {
  iconoirPlus,
  iconoirChatBubbleWarning,
  iconoirTrash,
  iconoirRefreshCircle,
  iconoirOpenNewWindow
} from '@ng-icons/iconoir'
import { SearchInputComponent } from '../../shared/components/search-input/search-input.component'
import { QuickCreationComponent } from '../../shared/components/quick-creation/quick-creation.component'
import { RecurrenceLabelPipe } from '../../shared/pipes/recurrence-label.pipe'
import {
  MultiSelectChoice,
  MultiSelectDropdownComponent
} from '../../shared/components/multi-select-dropdown/multi-select-dropdown.component'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
import {
  EMPTY_IMPORT_TYPE,
  PREFILLED_IMPORT_TYPE
} from '../../core/stores/integrity-link.store'
import { IntlinkNavService } from '../../core/layout/intlink-nav.service'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

marker('integrityLinks.view')
marker('integrityLinks.visibility.open')
marker('integrityLinks.visibility.restricted')
marker('integrityLinks.visibility.unconfigured')

const DEBOUNCE_TIME = 300

@Component({
  selector: 'app-integrity-link-list',
  imports: [
    DatePipe,
    TranslatePipe,
    NgIconComponent,
    SearchInputComponent,
    QuickCreationComponent,
    RecurrenceLabelPipe,
    MultiSelectDropdownComponent
  ],
  templateUrl: './integrity-link-list.component.html',
  providers: [
    provideIcons({
      iconoirPlus,
      iconoirChatBubbleWarning,
      iconoirTrash,
      iconoirRefreshCircle,
      iconoirOpenNewWindow
    })
  ]
})
export class IntegrityLinkListComponent {
  readonly emptyImportType = EMPTY_IMPORT_TYPE

  private api = inject(Api)
  private router = inject(Router)
  private translate = inject(TranslateService)
  private matDialog = inject(MatDialog)
  private operationToastStore = inject(OperationToastStore)
  private navService = inject(IntlinkNavService)

  integrityLinks = signal<IntegrityLinkListItem[]>([])
  loading = signal<boolean>(true)
  hasMore = signal<boolean>(false)
  loadingMore = signal<boolean>(false)
  searchQuery = signal('')
  selectedAccess = signal<string[]>([])
  selectedRecurrence = signal<string[]>([])
  // Statut/Référence have no backend support yet — placeholder dropdowns
  // for layout only, not wired into filters/reload.
  selectedStatus = signal<string[]>([])
  selectedReference = signal<string[]>([])
  readonly statusChoices: MultiSelectChoice[] = []
  readonly referenceChoices: MultiSelectChoice[] = []
  deleting = signal<string | null>(null)
  private nextOffset = signal(0)

  readonly accessChoices: MultiSelectChoice[] = PUBLIC_ACCESS.map((id) => ({
    id,
    label: `integrityLinks.visibility.${id}`
  }))
  readonly recurrenceChoices: MultiSelectChoice[] = RECURRENCE_PRESET.map(
    (id) => ({ id, label: `recurrence.preset.${id}` })
  )

  hasActiveFilters = computed(
    () =>
      this.searchQuery().length > 0 ||
      this.selectedAccess().length > 0 ||
      this.selectedRecurrence().length > 0
  )

  private filters = computed(() => ({
    search: this.searchQuery(),
    access: this.selectedAccess(),
    recurrence: this.selectedRecurrence()
  }))

  private reloadSubject = new Subject<void>()
  private requestId = 0

  constructor() {
    effect(() => {
      this.filters()
      this.reloadSubject.next()
    })
    this.reloadSubject
      .pipe(
        map(() => JSON.stringify(this.filters())),
        debounceTime(DEBOUNCE_TIME),
        // seed with the initial filters so the constructor load is not repeated
        startWith(JSON.stringify(this.filters())),
        distinctUntilChanged(),
        skip(1),
        takeUntilDestroyed()
      )
      .subscribe(() => {
        this.loading.set(true)
        this.loadIntegrityLinks()
      })
    this.loadIntegrityLinks()
  }

  private async loadIntegrityLinks(append = false): Promise<void> {
    const requestId = ++this.requestId
    if (!append) {
      this.hasMore.set(false)
      this.nextOffset.set(0)
    }
    try {
      const offset = append ? this.nextOffset() : 0
      const search = this.searchQuery() || undefined
      const access = this.selectedAccess().length
        ? (this.selectedAccess() as PublicAccess[])
        : undefined
      const recurrence = this.selectedRecurrence().length
        ? (this.selectedRecurrence() as RecurrencePreset[])
        : undefined
      const response = await this.api.invoke(
        listIntegrityLinksIngestionIntegrityLinksGet,
        { offset, search, access, recurrence }
      )
      if (requestId !== this.requestId) return
      if (append) {
        this.integrityLinks.update((items) => [...items, ...response.items])
      } else {
        this.integrityLinks.set(response.items)
      }
      this.hasMore.set(response.has_more)
      this.nextOffset.set(response.next_offset)
    } catch (error) {
      console.error('Failed to load integrity links:', error)
    } finally {
      if (requestId === this.requestId) {
        this.loading.set(false)
        this.loadingMore.set(false)
      }
    }
  }

  loadMore(): void {
    this.loadingMore.set(true)
    this.loadIntegrityLinks(true)
  }

  onRowClick(link: IntegrityLinkListItem): void {
    if (this.isReadOnly(link)) return
    if (
      !link.has_final_table &&
      link.source_import_type !== EMPTY_IMPORT_TYPE &&
      link.source_import_type !== PREFILLED_IMPORT_TYPE
    ) {
      this.router.navigate(['/', 'import', link.id], {
        queryParams: { step: 2 }
      })
    } else {
      this.router.navigate(['/', link.id, 'edit'])
    }
  }

  onRowKeydown(event: Event, link: IntegrityLinkListItem): void {
    // ignore Enter presses bubbling up from the action buttons
    if (event.target !== event.currentTarget) return
    this.onRowClick(link)
  }

  getCatalogueUrl(link: IntegrityLinkListItem): string | null {
    return this.navService.catalogueUrl(link.metadata_id)
  }

  onViewClick(event: Event, link: IntegrityLinkListItem): void {
    event.stopPropagation()
    this.navService.openCatalogue(link.metadata_id)
  }

  isReadOnly(link: IntegrityLinkListItem): boolean {
    return link.access_level === 'READ'
  }

  canDelete(link: IntegrityLinkListItem): boolean {
    return link.access_level === 'OWNER' || link.access_level === 'ADMIN'
  }

  async deleteIntegrityLink(event: Event, id: string): Promise<void> {
    event.stopPropagation()
    ;(event.currentTarget as HTMLElement)?.blur()
    if (this.deleting()) return
    const dialogRef = this.matDialog.open(ConfirmationDialogComponent, {
      data: {
        title: this.translate.instant('dashboard.deleteDataset'),
        message: this.translate.instant('dashboard.deleteDatasetConfirm'),
        confirmText: this.translate.instant('common.delete'),
        cancelText: this.translate.instant('common.cancel'),
        focusCancel: 'cancel'
      }
    })
    const confirmed = await firstValueFrom(dialogRef.afterClosed())
    if (!confirmed) return
    this.deleting.set(id)
    try {
      await this.api.invoke(
        deleteIntegrityLinkIngestionIntegrityLinkIntegrityLinkIdDelete,
        { integrity_link_id: id }
      )
      this.integrityLinks.update((items) => items.filter((l) => l.id !== id))
    } catch (error) {
      console.error('Failed to delete integrity link:', error)
      this.operationToastStore.addError('deletion')
    } finally {
      this.deleting.set(null)
    }
  }
}
