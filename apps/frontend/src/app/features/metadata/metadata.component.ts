import { CommonModule } from '@angular/common'
import { Component, effect, inject } from '@angular/core'
import { toSignal } from '@angular/core/rxjs-interop'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import {
  iconoirNumber1Square,
  iconoirNumber2Square,
  iconoirNumber3Square
} from '@ng-icons/iconoir'
import { TranslateDirective, TranslatePipe } from '@ngx-translate/core'
import {
  ButtonComponent,
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface
} from 'geonetwork-ui'
import { combineLatest, firstValueFrom, map, take, tap } from 'rxjs'
import { IntegrityLinkStore } from '../../layout/integrity-link.store'

@Component({
  selector: 'app-metadata',
  imports: [
    CommonModule,
    NgIconComponent,
    ButtonComponent,
    TranslateDirective,
    TranslatePipe,
    RecordFormComponent
  ],
  templateUrl: './metadata.component.html',
  styleUrl: './metadata.component.css',
  host: { class: 'flex-1 min-h-0 flex flex-col overflow-y-auto' },
  providers: [
    provideIcons({
      iconoirNumber1Square,
      iconoirNumber2Square,
      iconoirNumber3Square
    })
  ]
})
export class MetadataComponent {
  private recordsRepository = inject(RecordsRepositoryInterface)
  protected editor = inject(EditorFacade)
  readonly store = inject(IntegrityLinkStore)

  isRecordLoaded = toSignal(this.editor.record$.pipe(map((record) => !!record)))
  pages = toSignal(
    this.editor.editorConfig$.pipe(map((config) => config.pages))
  )
  currentPage$ = this.editor.currentPage$
  pagesLength$ = this.editor.editorConfig$.pipe(
    map((config) => config.pages.length)
  )
  isLastPage$ = combineLatest([this.currentPage$, this.pagesLength$]).pipe(
    map(([currentPage, pagesCount]) => currentPage >= pagesCount - 1)
  )

  constructor() {
    effect(() => {
      const integrityLink = this.store.integrityLink()
      if (integrityLink) {
        this.loadMetadata(integrityLink.metadata_id)
      }
    })
  }

  private loadMetadata(metadataId: string): void {
    try {
      this.recordsRepository
        .openRecordForEdition(metadataId)
        .pipe(
          take(1),
          tap(([currentRecord, currentRecordSource]) => {
            this.editor.openRecord(currentRecord, currentRecordSource)
          })
        )
        .subscribe()
    } catch (error) {
      console.error('Error loading metadata:', error)
    }
  }

  pageSectionClickHandler(index: number) {
    this.editor.setCurrentPage(index)
  }

  isCurrentPage(index: number) {
    return this.editor.currentPage$.pipe(
      map((currentPage) => currentPage === index)
    )
  }

  async previousPageButtonHandler() {
    const currentPage = await firstValueFrom(this.currentPage$)
    this.editor.setCurrentPage(currentPage - 1)
    window.scroll({
      top: 0
    })
  }

  async nextPageButtonHandler() {
    const currentPage = await firstValueFrom(this.currentPage$)
    this.editor.setCurrentPage(currentPage + 1)
    window.scroll({
      top: 0
    })
  }
}
