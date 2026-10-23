import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { signal } from '@angular/core'
import { firstValueFrom } from 'rxjs'
import {
  provideGn4,
  provideI18n,
  provideRepositoryUrl,
  TRANSLATE_DEFAULT_CONFIG
} from 'geonetwork-ui'
import { DatafeederRepository } from './datafeeder.repository'
import { IntegrityLinkStore } from './integrity-link.store'
import { Api } from '../api/api'
import { IntegrityLinkResponse } from '../api/models'
import { updateIsReferenceIngestionIntegrityLinkIntegrityLinkIdIsReferencePatch } from '../api/functions'

describe('DatafeederRepository', () => {
  let repository: DatafeederRepository
  let mockApi: { invoke: ReturnType<typeof vi.fn> }
  let integrityLink: ReturnType<typeof signal<IntegrityLinkResponse | null>>

  beforeEach(() => {
    mockApi = { invoke: vi.fn().mockResolvedValue({}) }
    integrityLink = signal<IntegrityLinkResponse | null>({
      id: 'intlink-1',
      is_reference_dataset: true
    } as IntegrityLinkResponse)

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideI18n(TRANSLATE_DEFAULT_CONFIG),
        provideRepositoryUrl(() => '/geonetwork/srv/api'),
        provideGn4({ disableDraft: true }),
        { provide: Api, useValue: mockApi },
        { provide: IntegrityLinkStore, useValue: { integrityLink } }
      ]
    })

    repository = TestBed.inject(DatafeederRepository)
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

    it('throws on an unknown flag', () => {
      expect(() =>
        repository.getRecordFlag('record-uuid', 'UNKNOWN' as any)
      ).toThrow('Unknown record flag: UNKNOWN')
    })
  })

  describe('setRecordFlag', () => {
    it('calls the is_reference endpoint for the current integrity link', async () => {
      await firstValueFrom(
        repository.setRecordFlag('record-uuid', 'IS_REFERENCE_DATASET', false)
      )

      expect(mockApi.invoke).toHaveBeenCalledWith(
        updateIsReferenceIngestionIntegrityLinkIntegrityLinkIdIsReferencePatch,
        { integrity_link_id: 'intlink-1', body: { is_reference: false } }
      )
    })

    it('propagates API errors', async () => {
      mockApi.invoke.mockRejectedValue(new Error('Forbidden'))

      await expect(
        firstValueFrom(
          repository.setRecordFlag('record-uuid', 'IS_REFERENCE_DATASET', true)
        )
      ).rejects.toThrow('Forbidden')
    })

    it('throws on an unknown flag without calling the API', () => {
      expect(() =>
        repository.setRecordFlag('record-uuid', 'UNKNOWN' as any, true)
      ).toThrow('Unknown record flag: UNKNOWN')
      expect(mockApi.invoke).not.toHaveBeenCalled()
    })
  })
})
