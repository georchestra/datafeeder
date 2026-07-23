import { ComponentFixture, TestBed } from '@angular/core/testing'
import { Component, Input } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { TranslateModule } from '@ngx-translate/core'
import { NgIconComponent } from '@ng-icons/core'
import { EditorFacade } from 'geonetwork-ui'
import { BehaviorSubject, of } from 'rxjs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Api } from '../../core/api/api'
import { IntegrityLinkStore } from '../../core/stores/integrity-link.store'
import { OperationToastStore } from '../../core/stores/operation-toast.store'
import { AiGenerateButtonComponent } from './ai-generate-button.component'

@Component({ selector: 'ng-icon', standalone: true, template: '' })
class MockNgIconComponent {
  @Input() name: any
  @Input() size: any
}

describe('AiGenerateButtonComponent', () => {
  let component: AiGenerateButtonComponent
  let fixture: ComponentFixture<AiGenerateButtonComponent>

  let mockApi: { invoke: ReturnType<typeof vi.fn> }
  let mockEditorFacade: any
  let mockStore: any
  let mockMatDialog: { open: ReturnType<typeof vi.fn> }
  let mockToastStore: {
    addAISuccess: ReturnType<typeof vi.fn>
    addError: ReturnType<typeof vi.fn>
  }

  let recordSubject: BehaviorSubject<any>

  beforeEach(async () => {
    recordSubject = new BehaviorSubject<any>(null)

    mockEditorFacade = {
      record$: recordSubject.asObservable(),
      changedSinceSave$: of(false),
      updateRecordField: vi.fn()
    }

    mockStore = {
      intlinkId: vi.fn().mockReturnValue('test-intlink-id')
    }

    mockApi = {
      invoke: vi.fn().mockResolvedValue({
        title: 'Generated Title',
        abstract: 'Generated abstract.',
        keywords: ['kw1', 'kw2'],
        topic_categories: ['transportation']
      })
    }

    mockMatDialog = {
      open: vi.fn().mockReturnValue({ afterClosed: () => of(true) })
    }

    mockToastStore = {
      addAISuccess: vi.fn(),
      addError: vi.fn()
    }

    await TestBed.configureTestingModule({
      imports: [AiGenerateButtonComponent, TranslateModule.forRoot()],
      providers: [
        { provide: Api, useValue: mockApi },
        { provide: EditorFacade, useValue: mockEditorFacade },
        { provide: IntegrityLinkStore, useValue: mockStore },
        { provide: MatDialog, useValue: mockMatDialog },
        { provide: OperationToastStore, useValue: mockToastStore }
      ]
    })
      .overrideComponent(AiGenerateButtonComponent, {
        remove: { imports: [NgIconComponent] },
        add: { imports: [MockNgIconComponent] }
      })
      .compileComponents()

    fixture = TestBed.createComponent(AiGenerateButtonComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('initial state', () => {
    it('should default to rewrite mode', () => {
      expect(component.lastAiMode()).toBe('rewrite')
    })

    it('should not be generating', () => {
      expect(component.isGeneratingAI()).toBe(false)
    })
  })

  describe('onGenerateWithAI()', () => {
    const mockRecord = {
      title: 'My Title',
      abstract: 'My abstract',
      keywords: [{ label: 'kw1', type: 'theme' }],
      topics: ['transportation']
    }

    beforeEach(() => {
      recordSubject.next(mockRecord)
    })

    it('should set lastAiMode', async () => {
      await component.onGenerateWithAI('rewrite')
      expect(component.lastAiMode()).toBe('rewrite')
    })

    it('should call the API with mode and current values', async () => {
      await component.onGenerateWithAI('regenerate')
      expect(mockApi.invoke).toHaveBeenCalledOnce()
      const body = mockApi.invoke.mock.calls[0][1].body
      expect(body.mode).toBe('regenerate')
      expect(body.current_values).toMatchObject({
        title: 'My Title',
        abstract: 'My abstract',
        keywords: 'kw1',
        topics: 'transportation'
      })
    })

    it('should update all fields in the editor', async () => {
      await component.onGenerateWithAI('regenerate')
      expect(mockEditorFacade.updateRecordField).toHaveBeenCalledWith(
        'title',
        'Generated Title'
      )
      expect(mockEditorFacade.updateRecordField).toHaveBeenCalledWith(
        'abstract',
        'Generated abstract.'
      )
      expect(mockEditorFacade.updateRecordField).toHaveBeenCalledWith(
        'keywords',
        expect.anything()
      )
      expect(mockEditorFacade.updateRecordField).toHaveBeenCalledWith(
        'topics',
        expect.anything()
      )
    })

    it('should show success toast after generation', async () => {
      await component.onGenerateWithAI('regenerate')
      expect(mockToastStore.addAISuccess).toHaveBeenCalledWith(
        'info.operation.aiMetadataGeneration'
      )
    })

    it('should reset isGeneratingAI to false after success', async () => {
      await component.onGenerateWithAI('regenerate')
      expect(component.isGeneratingAI()).toBe(false)
    })

    it('should show error toast and reset isGeneratingAI on API failure', async () => {
      mockApi.invoke.mockRejectedValueOnce(new Error('Network error'))
      await component.onGenerateWithAI('regenerate')
      expect(mockToastStore.addError).toHaveBeenCalledWith(
        'aiMetadataGeneration'
      )
      expect(component.isGeneratingAI()).toBe(false)
    })

    it('should not call the API if intlinkId is missing', async () => {
      mockStore.intlinkId.mockReturnValue(null)
      await component.onGenerateWithAI('regenerate')
      expect(mockApi.invoke).not.toHaveBeenCalled()
    })

    it('should send null current_values when record is empty', async () => {
      recordSubject.next({ title: '', abstract: '', keywords: [], topics: [] })
      await component.onGenerateWithAI('regenerate')
      const body = mockApi.invoke.mock.calls[0][1].body
      expect(body.current_values).toBeNull()
    })

    describe('with unsaved changes', () => {
      beforeEach(() => {
        mockEditorFacade.changedSinceSave$ = of(true)
        // Recreate component with updated facade
        fixture = TestBed.createComponent(AiGenerateButtonComponent)
        component = fixture.componentInstance
        recordSubject.next(mockRecord)
        fixture.detectChanges()
      })

      it('should open confirmation dialog when there are unsaved changes', async () => {
        await component.onGenerateWithAI('regenerate')
        expect(mockMatDialog.open).toHaveBeenCalled()
      })

      it('should not call API if user cancels the dialog', async () => {
        mockMatDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) })
        await component.onGenerateWithAI('regenerate')
        expect(mockApi.invoke).not.toHaveBeenCalled()
      })

      it('should call API if user confirms the dialog', async () => {
        mockMatDialog.open.mockReturnValueOnce({ afterClosed: () => of(true) })
        await component.onGenerateWithAI('regenerate')
        expect(mockApi.invoke).toHaveBeenCalled()
      })
    })
  })
})
