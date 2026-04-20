import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  Injector,
  output,
  signal,
  ViewChild
} from '@angular/core'
import { Router } from '@angular/router'
import { TranslatePipe } from '@ngx-translate/core'
import { NgIconComponent, provideIcons } from '@ng-icons/core'
import { iconoirNavArrowDown, iconoirPlus } from '@ng-icons/iconoir'
import { Api } from '../../../core/api/api'
import { createEmptyDatasetIngestionIntegrityLinkEmptyPost } from '../../../core/api/functions'
import { marker } from '@biesbjerg/ngx-translate-extract-marker'
import { ErrorToastStore } from '../../../core/stores/error-toast.store'

marker('quickImport.modeEmpty')
marker('quickImport.modeWithData')
marker('quickImport.button')
marker('quickImport.titleLabel')
marker('quickImport.titlePlaceholder')
marker('quickImport.create')
marker('errors.operation.emptyDatasetCreate')

type ImportMode = 'empty' | 'with-data'

const SESSION_KEY = 'quickImport.mode'

@Component({
  selector: 'app-quick-creation',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslatePipe, NgIconComponent],
  templateUrl: './quick-creation.component.html',
  providers: [provideIcons({ iconoirPlus, iconoirNavArrowDown })]
})
export class QuickCreationComponent {
  private readonly api = inject(Api)
  private readonly router = inject(Router)
  private readonly injector = inject(Injector)
  private readonly errorToastStore = inject(ErrorToastStore)

  @ViewChild('titleInput') titleInputRef?: ElementRef<HTMLInputElement>

  datasetCreated = output<string>()

  mode = signal<ImportMode>(
    (sessionStorage.getItem(SESSION_KEY) as ImportMode | null) ?? 'empty'
  )
  isFormOpen = signal(false)
  isMenuOpen = signal(false)
  title = signal('')
  submitting = signal(false)

  buttonLabel = computed(() =>
    this.mode() === 'empty'
      ? 'quickImport.modeEmpty'
      : 'quickImport.modeWithData'
  )

  triggerAction() {
    this.closeMenu()
    if (this.mode() === 'with-data') {
      this.router.navigate(['/', 'import'])
    } else {
      this.toggleForm()
    }
  }

  toggleForm() {
    this.isFormOpen.update((v) => !v)
    if (!this.isFormOpen()) {
      this.title.set('')
    } else {
      afterNextRender(() => this.titleInputRef?.nativeElement.focus(), {
        injector: this.injector
      })
    }
  }

  closeForm() {
    this.isFormOpen.set(false)
    this.title.set('')
  }

  toggleMenu() {
    this.isMenuOpen.update((v) => !v)
  }

  closeMenu() {
    this.isMenuOpen.set(false)
  }

  selectMode(mode: ImportMode) {
    this.mode.set(mode)
    sessionStorage.setItem(SESSION_KEY, mode)
    this.closeMenu()
    this.closeForm()
    this.triggerAction()
  }

  async submit() {
    if (!this.title().trim()) return
    this.submitting.set(true)
    try {
      const result = await this.api.invoke(
        createEmptyDatasetIngestionIntegrityLinkEmptyPost,
        {
          body: { title: this.title().trim() }
        }
      )
      this.datasetCreated.emit(this.title())
      this.closeForm()
      this.router.navigate(['/', String(result.id), 'edit'])
    } catch (error) {
      this.errorToastStore.add('emptyDatasetCreate', error)
    } finally {
      this.submitting.set(false)
    }
  }
}
