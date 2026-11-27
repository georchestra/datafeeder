import { TestBed } from '@angular/core/testing'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { Signal, signal } from '@angular/core'
import { firstValueFrom } from 'rxjs'
import {
  markRecordAsChanged,
  provideGn4,
  provideI18n,
  provideRepositoryUrl,
  TRANSLATE_DEFAULT_CONFIG
} from 'geonetwork-ui'
import { Store } from '@ngrx/store'
import { DatafeederRepository } from './datafeeder.repository'
import { IntegrityLinkStore } from './integrity-link.store'
import { IntegrityLinkResponse } from '../api/models'

describe('DatafeederRepository', () => {
  let repository: DatafeederRepository
  let mockEditorStore
  let integrityLink: Signal<IntegrityLinkResponse>
  let isReferenceDatasetChanged: Signal<boolean>
  let httpController: HttpTestingController

  beforeEach(() => {
    mockEditorStore = { dispatch: vi.fn() }
    integrityLink = signal<IntegrityLinkResponse>({
      id: 'intlink-1',
      is_reference_dataset: true
    } as IntegrityLinkResponse)
    isReferenceDatasetChanged = signal(false)

    TestBed.configureTestingModule({
      providers: [
        provideI18n(TRANSLATE_DEFAULT_CONFIG),
        provideRepositoryUrl(() => '/geonetwork/srv/api'),
        provideGn4({ disableDraft: true }),
        { provide: Store, useValue: mockEditorStore },
        {
          provide: IntegrityLinkStore,
          useValue: { integrityLink, isReferenceDatasetChanged }
        },
        provideHttpClientTesting()
      ]
    })

    httpController = TestBed.inject(HttpTestingController)
    repository = TestBed.inject(DatafeederRepository)
    httpController.expectOne('./assets/i18n/en.json').flush({})
  })

  afterEach(() => {
    httpController.verify()
  })

  it('should be created', () => {
    expect(repository).toBeTruthy()
  })

  describe('getRecordFlag', () => {
    it('returns the reference flag of the current integrity link', async () => {
      const value = await firstValueFrom(
        repository.getRecordFlag('record-uuid', 'IS_REFERENCE_DATASET')
      )
      expect(value).toBe(true)
    })

    it('does not call the GN4 API', async () => {
      await firstValueFrom(
        repository.getRecordFlag('record-uuid', 'IS_REFERENCE_DATASET')
      )
      httpController.expectNone((req) =>
        req.url.startsWith('/geonetwork/srv/api/')
      )
    })

    it('throws on an unknown flag', () => {
      expect(() =>
        repository.getRecordFlag('record-uuid', 'UNKNOWN' as any)
      ).toThrow('Unknown record flag: UNKNOWN')
    })
  })

  describe('setRecordFlag', () => {
    it('updates the local flag, marks it as changed, and marks the record as changed', async () => {
      await firstValueFrom(
        repository.setRecordFlag('record-uuid', 'IS_REFERENCE_DATASET', false)
      )

      expect(integrityLink()).toEqual({
        id: 'intlink-1',
        is_reference_dataset: false
      })
      expect(isReferenceDatasetChanged()).toBe(true)
      expect(mockEditorStore.dispatch).toHaveBeenCalledWith(
        markRecordAsChanged()
      )
    })

    it('does not call the GN4 API', async () => {
      await firstValueFrom(
        repository.setRecordFlag('record-uuid', 'IS_REFERENCE_DATASET', false)
      )
      httpController.expectNone((req) =>
        req.url.startsWith('/geonetwork/srv/api/')
      )
    })

    it('throws on an unknown flag without changing local state', () => {
      expect(() =>
        repository.setRecordFlag('record-uuid', 'UNKNOWN' as any, true)
      ).toThrow('Unknown record flag: UNKNOWN')
    })
  })
})
