import { TestBed } from '@angular/core/testing'
import { signal } from '@angular/core'
import { of } from 'rxjs'
import { EditorFacade, findConverterForDocument } from 'geonetwork-ui'
import { MetadataSaveService } from './metadata-save.service'
import { Api } from '../api/api'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import { OperationToastStore } from '../stores/operation-toast.store'

vi.mock('geonetwork-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('geonetwork-ui')>()
  return {
    ...actual,
    findConverterForDocument: vi.fn()
  }
})

const RECORD = { uuid: 'abc', title: 'My Dataset' } as any
const SOURCE = '<xml>source</xml>'
const SERIALIZED = '<xml>serialized</xml>'
const UPDATED_INTLINK = { integrity_title: 'Updated Title' }

function setup() {
  const mockEditor = {
    record$: of(RECORD),
    recordSource$: of(SOURCE)
  }

  const integrityLinkSignal = signal({
    id: 'intlink-1',
    integrity_title: 'Original Title'
  } as any)

  const mockStore = {
    integrityLink: integrityLinkSignal
  }

  const mockApi = {
    invoke: vi.fn().mockResolvedValue(UPDATED_INTLINK)
  }

  const mockToastStore = {
    addInfo: vi.fn(),
    addError: vi.fn()
  }

  const mockConverter = {
    writeRecord: vi.fn().mockResolvedValue(SERIALIZED)
  }
  vi.mocked(findConverterForDocument).mockReturnValue(mockConverter as any)

  TestBed.configureTestingModule({
    providers: [
      MetadataSaveService,
      { provide: EditorFacade, useValue: mockEditor },
      { provide: Api, useValue: mockApi },
      { provide: IntegrityLinkStore, useValue: mockStore },
      { provide: OperationToastStore, useValue: mockToastStore }
    ]
  })

  const service = TestBed.inject(MetadataSaveService)

  return { service, mockApi, mockToastStore, mockConverter, mockStore }
}

describe('MetadataSaveService', () => {
  describe('isSaving signal', () => {
    it('should start as false', () => {
      const { service } = setup()
      expect(service.isSaving()).toBe(false)
    })

    it('should be true while save is in progress and false after completion', async () => {
      const { service, mockConverter } = setup()
      let sawSavingTrue = false
      mockConverter.writeRecord.mockImplementation(async () => {
        sawSavingTrue = service.isSaving()
        return SERIALIZED
      })
      await service.save()
      expect(sawSavingTrue).toBe(true)
      expect(service.isSaving()).toBe(false)
    })

    it('should reset to false even when save throws', async () => {
      const { service, mockConverter } = setup()
      mockConverter.writeRecord.mockRejectedValue(new Error('network'))
      await expect(service.save()).rejects.toThrow()
      expect(service.isSaving()).toBe(false)
    })
  })

  describe('when already saving', () => {
    it('should not call the API a second time', async () => {
      const { service, mockApi, mockConverter } = setup()
      // Start a save that never resolves so isSaving stays true
      mockConverter.writeRecord.mockReturnValue(new Promise(() => undefined))
      service.save()
      await service.save()
      expect(mockApi.invoke).not.toHaveBeenCalled()
    })
  })

  describe('on success', () => {
    it('should serialize the record using findConverterForDocument', async () => {
      const { service, mockConverter } = setup()
      await service.save()
      expect(findConverterForDocument).toHaveBeenCalledWith(SOURCE)
      expect(mockConverter.writeRecord).toHaveBeenCalledWith(RECORD, SOURCE)
    })

    it('should call the update metadata API with serialized XML and title', async () => {
      const { service, mockApi } = setup()
      await service.save()
      expect(mockApi.invoke).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          integrity_link_id: 'intlink-1',
          body: { serialized_xml: SERIALIZED, title: RECORD.title }
        })
      )
    })

    it('should update the integrity_title in the store', async () => {
      const { service, mockStore } = setup()
      await service.save()
      expect(mockStore.integrityLink().integrity_title).toBe('Updated Title')
    })

    it('should add an info toast', async () => {
      const { service, mockToastStore } = setup()
      await service.save()
      expect(mockToastStore.addInfo).toHaveBeenCalledWith('metadataSave')
    })

    it('should not add an error toast', async () => {
      const { service, mockToastStore } = setup()
      await service.save()
      expect(mockToastStore.addError).not.toHaveBeenCalled()
    })
  })

  describe('on error', () => {
    it('should add an error toast', async () => {
      const { service, mockConverter, mockToastStore } = setup()
      mockConverter.writeRecord.mockRejectedValue(new Error('network'))
      await expect(service.save()).rejects.toThrow()
      expect(mockToastStore.addError).toHaveBeenCalledWith('metadataSave')
    })

    it('should rethrow the error', async () => {
      const { service, mockConverter } = setup()
      mockConverter.writeRecord.mockRejectedValue(new Error('network'))
      await expect(service.save()).rejects.toThrow('network')
    })

    it('should not add an info toast', async () => {
      const { service, mockConverter, mockToastStore } = setup()
      mockConverter.writeRecord.mockRejectedValue(new Error('network'))
      await expect(service.save()).rejects.toThrow()
      expect(mockToastStore.addInfo).not.toHaveBeenCalled()
    })
  })
})
