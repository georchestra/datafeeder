import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing'
import { SettingsService, ProjectionSetting } from './settings.service'
import { ApiConfiguration } from '../api/api-configuration'
import { provideRouter } from '@angular/router'

describe('SettingsService', () => {
  let service: SettingsService
  let httpMock: HttpTestingController

  const mockBackendProjections: ProjectionSetting[] = [
    { value: 'EPSG:4326', label: 'WGS 84' },
    { value: 'EPSG:3857', label: 'Web Mercator' },
    { value: 'EPSG:2154', label: 'Lambert 93' }
  ]

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ApiConfiguration,
          useValue: { rootUrl: 'http://localhost:8000' }
        },
        SettingsService
      ]
    }).compileComponents()

    service = TestBed.inject(SettingsService)
    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    httpMock.verify()
  })

  it('should be created', () => {
    expect(service).toBeTruthy()
  })

  describe('initial state', () => {
    it('should have null settings initially', () => {
      expect(service.currentSettings()).toBeNull()
    })

    it('should not be loading initially', () => {
      expect(service.isLoading()).toBe(false)
    })

    it('should have no error initially', () => {
      expect(service.errorMessage()).toBeNull()
    })
  })

  describe('loadSettings', () => {
    it('should load settings from backend successfully', async () => {
      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      expect(req.request.method).toBe('GET')
      req.flush({ projections: mockBackendProjections })

      const result = await loadPromise

      expect(result.projections).toHaveLength(3)
      expect(result.projections).toEqual(mockBackendProjections)
      expect(service.currentSettings()).toEqual(result)
      expect(service.isLoading()).toBe(false)
    })

    it('should merge backend projections with defaults', async () => {
      const backendProjections = [{ value: 'EPSG:2154', label: 'Lambert 93' }]

      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: backendProjections })

      const result = await loadPromise

      expect(result.projections).toHaveLength(3)
      // Should contain defaults + backend
      expect(result.projections?.some((p) => p.value === 'EPSG:4326')).toBe(
        true
      )
      expect(result.projections?.some((p) => p.value === 'EPSG:3857')).toBe(
        true
      )
      expect(result.projections?.some((p) => p.value === 'EPSG:2154')).toBe(
        true
      )
    })

    it('should use cached settings on subsequent calls', async () => {
      const loadPromise1 = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: mockBackendProjections })

      const result1 = await loadPromise1
      const result2 = await service.loadSettings()

      // No second HTTP request should be made
      httpMock.expectNone('http://localhost:8000/settings/')
      expect(result1).toEqual(result2)
    })

    it('should set loading state during API call', async () => {
      const loadPromise = service.loadSettings()

      // Check loading state is true before responding
      expect(service.isLoading()).toBe(true)

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: mockBackendProjections })

      await loadPromise

      expect(service.isLoading()).toBe(false)
    })

    it('should handle API errors and use default projections', async () => {
      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.error(new ProgressEvent('Network error'))

      const result = await loadPromise

      expect(result.projections).toHaveLength(2)
      expect(result.projections).toEqual([
        { value: 'EPSG:4326', label: 'WGS 84' },
        { value: 'EPSG:3857', label: 'Web Mercator' }
      ])
      expect(service.errorMessage()).toBeTruthy()
      expect(service.isLoading()).toBe(false)
    })

    it('should handle empty backend projections', async () => {
      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: [] })

      const result = await loadPromise

      // Should still have defaults
      expect(result.projections).toHaveLength(2)
      expect(result.projections).toEqual([
        { value: 'EPSG:4326', label: 'WGS 84' },
        { value: 'EPSG:3857', label: 'Web Mercator' }
      ])
    })
  })

  describe('getProjections', () => {
    it('should return empty array when settings not loaded', () => {
      expect(service.getProjections()).toEqual([])
    })

    it('should return projections after settings loaded', async () => {
      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: mockBackendProjections })

      await loadPromise
      const projections = service.getProjections()

      expect(projections).toEqual(mockBackendProjections)
    })
  })

  describe('getSetting', () => {
    it('should return undefined when settings not loaded', () => {
      expect(
        service.getSetting<ProjectionSetting[]>('projections')
      ).toBeUndefined()
    })

    it('should return setting value after settings loaded', async () => {
      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: mockBackendProjections })

      await loadPromise
      const projections = service.getSetting<ProjectionSetting[]>('projections')

      expect(projections).toEqual(mockBackendProjections)
    })
  })

  describe('projection merging', () => {
    it('should override default projection with backend value', async () => {
      const backendProjections = [
        { value: 'EPSG:4326', label: 'Custom WGS 84 Label' }
      ]

      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: backendProjections })

      const result = await loadPromise

      const wgs84 = result.projections?.find((p) => p.value === 'EPSG:4326')
      expect(wgs84?.label).toBe('Custom WGS 84 Label')
    })

    it('should preserve order with defaults first', async () => {
      const backendProjections = [{ value: 'EPSG:2154', label: 'Lambert 93' }]

      const loadPromise = service.loadSettings()

      const req = httpMock.expectOne('http://localhost:8000/settings/')
      req.flush({ projections: backendProjections })

      const result = await loadPromise

      // Defaults should be first
      expect(result.projections?.[0].value).toBe('EPSG:4326')
      expect(result.projections?.[1].value).toBe('EPSG:3857')
      expect(result.projections?.[2].value).toBe('EPSG:2154')
    })
  })
})
