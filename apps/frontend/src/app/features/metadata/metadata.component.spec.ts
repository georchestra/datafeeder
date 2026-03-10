import { Component, EventEmitter, Input, Output, signal } from '@angular/core'
import { ComponentFixture, TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { provideRouter } from '@angular/router'
import { NgIconComponent } from '@ng-icons/core'
import { TranslateModule } from '@ngx-translate/core'
import {
  ButtonComponent,
  DEFAULT_CONFIGURATION,
  EditorFacade,
  RecordFormComponent,
  RecordsRepositoryInterface
} from 'geonetwork-ui'
import { BehaviorSubject, firstValueFrom, of } from 'rxjs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Api } from '../../core/api/api'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { MetadataComponent } from './metadata.component'

@Component({ selector: 'gn-ui-button', standalone: true, template: '' })
class MockButtonComponent {
  @Input() type: any
  @Input() extraClass: any
  @Output() buttonClick = new EventEmitter<void>()
}

@Component({ selector: 'gn-ui-record-form', standalone: true, template: '' })
class MockRecordFormComponent {}

@Component({ selector: 'ng-icon', standalone: true, template: '' })
class MockNgIconComponent {
  @Input() name: any
  @Input() size: any
}

describe('MetadataComponent', () => {
  let component: MetadataComponent
  let fixture: ComponentFixture<MetadataComponent>

  let mockEditorFacade: any
  let mockRepo: any
  let mockIntegrityLinkStore: any
  let mockApi: any

  let recordSubject: BehaviorSubject<any>
  let configSubject: BehaviorSubject<any>
  let currentPageSubject: BehaviorSubject<number>

  const integrityLinkSignal = signal<any>(null)

  beforeEach(async () => {
    recordSubject = new BehaviorSubject(null)
    configSubject = new BehaviorSubject(
      JSON.parse(JSON.stringify(DEFAULT_CONFIGURATION))
    ) // Deep copy
    currentPageSubject = new BehaviorSubject(0)

    mockEditorFacade = {
      record$: recordSubject.asObservable(),
      editorConfig$: configSubject.asObservable(),
      currentPage$: currentPageSubject.asObservable(),
      setConfiguration: vi.fn(),
      openRecord: vi.fn(),
      setCurrentPage: vi.fn()
    }

    mockRepo = {
      openRecordForEdition: vi
        .fn()
        .mockReturnValue(of([{ uuid: '123' }, { id: 'src' }]))
    }

    mockIntegrityLinkStore = {
      integrityLink: integrityLinkSignal
    }

    mockApi = {
      invoke: vi.fn().mockResolvedValue({ dag_runs: [] })
    }

    window.scroll = vi.fn()

    await TestBed.configureTestingModule({
      imports: [MetadataComponent, TranslateModule.forRoot()],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        { provide: EditorFacade, useValue: mockEditorFacade },
        { provide: RecordsRepositoryInterface, useValue: mockRepo },
        { provide: IntegrityLinkStore, useValue: mockIntegrityLinkStore },
        { provide: Api, useValue: mockApi }
      ]
    })
      .overrideComponent(MetadataComponent, {
        remove: {
          imports: [ButtonComponent, NgIconComponent, RecordFormComponent]
        },
        add: {
          imports: [
            MockButtonComponent,
            MockRecordFormComponent,
            MockNgIconComponent
          ]
        }
      })
      .compileComponents()

    fixture = TestBed.createComponent(MetadataComponent)
    component = fixture.componentInstance
    integrityLinkSignal.set(null)
  })

  it('should create', () => {
    fixture.detectChanges()
    expect(component).toBeTruthy()
  })

  describe('Initialization & Configuration', () => {
    it('should customize configuration on init (ngOnInit)', () => {
      fixture.detectChanges()

      expect(mockEditorFacade.setConfiguration).toHaveBeenCalled()
      const callArgs = mockEditorFacade.setConfiguration.mock.calls[0][0]
      expect(callArgs.pages[1].sections.length).toBe(1)
    })
  })

  describe('Reactive Loading (Effect)', () => {
    it('should load metadata when processing status is success', async () => {
      const mockLink = { id: 'intlink-1', metadata_id: 'meta-123' }
      mockApi.invoke.mockResolvedValue({
        dag_runs: [{ dag_run_id: 'run-1', state: 'success' }]
      })

      integrityLinkSignal.set(mockLink)

      fixture.detectChanges()
      await fixture.whenStable()

      expect(mockRepo.openRecordForEdition).toHaveBeenCalledWith('meta-123')
      expect(mockEditorFacade.openRecord).toHaveBeenCalledWith(
        expect.objectContaining({ uuid: '123' }),
        expect.objectContaining({ id: 'src' })
      )
    })

    it('should NOT load metadata if processing status is not success', async () => {
      const mockLink = { id: 'intlink-1', metadata_id: 'meta-123' }
      mockApi.invoke.mockResolvedValue({
        dag_runs: [{ dag_run_id: 'run-1', state: 'failed' }]
      })

      integrityLinkSignal.set(mockLink)

      fixture.detectChanges()
      await fixture.whenStable()

      expect(mockRepo.openRecordForEdition).not.toHaveBeenCalled()
    })

    it('should NOT load metadata if integrityLink is null', async () => {
      integrityLinkSignal.set(null)
      fixture.detectChanges()
      await fixture.whenStable()
      expect(mockRepo.openRecordForEdition).not.toHaveBeenCalled()
    })
  })

  describe('Navigation & UI Interaction', () => {
    beforeEach(() => {
      fixture.detectChanges()
    })

    it('should set current page when clicking a section', () => {
      const pageIndex = 2
      component.pageSectionClickHandler(pageIndex)
      expect(mockEditorFacade.setCurrentPage).toHaveBeenCalledWith(pageIndex)
    })

    it('isCurrentPage should return true for matching index', async () => {
      currentPageSubject.next(1)

      const isCurrent = await firstValueFrom(component.isCurrentPage(1))
      const isNotCurrent = await firstValueFrom(component.isCurrentPage(0))

      expect(isCurrent).toBe(true)
      expect(isNotCurrent).toBe(false)
    })

    it('should change page when pageSectionClickHandler is called', () => {
      component.pageSectionClickHandler(2)
      expect(mockEditorFacade.setCurrentPage).toHaveBeenCalledWith(2)
    })

    it('should go to previous page and scroll top', async () => {
      currentPageSubject.next(2)
      await component.previousPageButtonHandler()
      expect(mockEditorFacade.setCurrentPage).toHaveBeenCalledWith(1)
      expect(window.scroll).toHaveBeenCalledWith({ top: 0 })
    })

    it('should go to next page and scroll top', async () => {
      currentPageSubject.next(1)
      await component.nextPageButtonHandler()
      expect(mockEditorFacade.setCurrentPage).toHaveBeenCalledWith(2)
      expect(window.scroll).toHaveBeenCalledWith({ top: 0 })
    })
  })

  describe('View Logic (Signals & Observables)', () => {
    it('isRecordLoaded should follow the editor record status', () => {
      fixture.detectChanges()
      expect(component.isRecordLoaded()).toBe(false)

      recordSubject.next({ id: 'loaded' })
      fixture.detectChanges()
      expect(component.isRecordLoaded()).toBe(true)
    })

    it('isLastPage$ should be true when on the last index', async () => {
      const config = { pages: [{}, {}] } // 2 pages
      configSubject.next(config)

      currentPageSubject.next(1) // Index 1 = Page 2
      const isLast = await firstValueFrom(component.isLastPage$)
      expect(isLast).toBe(true)
    })
  })
})
