import { signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import {
  ActivatedRouteSnapshot,
  RedirectCommand,
  Router,
  provideRouter
} from '@angular/router'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import {
  IntegrityLinkResolver,
  IntegrityLinkResolverWithRedirect
} from './integrity-link.resolver'

function makeRoute(
  params: Record<string, string> = {},
  parentParams: Record<string, string> = {}
): ActivatedRouteSnapshot {
  return {
    params,
    parent:
      parentParams && Object.keys(parentParams).length
        ? { params: parentParams }
        : null
  } as unknown as ActivatedRouteSnapshot
}

function createMockStore(
  overrides: Partial<{
    loadIntegrityLink: (id: string) => Promise<any>
    clearIntegrityLink: () => void
  }> = {}
) {
  return {
    intlinkId: signal<string | null>(null),
    integrityLink: signal(null),
    loadError: signal<'forbidden' | 'not_found' | 'server_error' | null>(null),
    loadIntegrityLink: vi.fn().mockResolvedValue({ id: 'uuid-1' }),
    clearIntegrityLink: vi.fn(),
    ...overrides
  }
}

describe('IntegrityLinkResolver', () => {
  let mockStore: ReturnType<typeof createMockStore>

  beforeEach(async () => {
    mockStore = createMockStore()

    await TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: IntegrityLinkStore, useValue: mockStore }
      ]
    }).compileComponents()
  })

  it('should load integrity link when intlink_id param is present', async () => {
    const route = makeRoute({ intlink_id: 'uuid-1' })
    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolver(route, {} as any)
    )

    expect(mockStore.loadIntegrityLink).toHaveBeenCalledWith('uuid-1')
    expect(result).toEqual({ id: 'uuid-1' })
  })

  it('should load integrity link from parent params', async () => {
    const route = makeRoute({}, { intlink_id: 'uuid-parent' })
    await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolver(route, {} as any)
    )

    expect(mockStore.loadIntegrityLink).toHaveBeenCalledWith('uuid-parent')
  })

  it('should clear store and return undefined when no intlink_id', async () => {
    const route = makeRoute()
    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolver(route, {} as any)
    )

    expect(mockStore.clearIntegrityLink).toHaveBeenCalled()
    expect(result).toBeUndefined()
  })

  it('should clear store and return undefined on load error (no redirect)', async () => {
    mockStore.loadIntegrityLink = vi.fn().mockRejectedValue({ status: 404 })
    const route = makeRoute({ intlink_id: 'uuid-missing' })

    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolver(route, {} as any)
    )

    expect(mockStore.clearIntegrityLink).toHaveBeenCalled()
    expect(result).toBeUndefined()
  })
})

describe('IntegrityLinkResolverWithRedirect', () => {
  let mockStore: ReturnType<typeof createMockStore>
  let router: Router

  beforeEach(async () => {
    mockStore = createMockStore()

    await TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: IntegrityLinkStore, useValue: mockStore }
      ]
    }).compileComponents()

    router = TestBed.inject(Router)
  })

  it('should return RedirectCommand to /import on 404', async () => {
    mockStore.loadIntegrityLink = vi.fn().mockRejectedValue({ status: 404 })
    const route = makeRoute({ intlink_id: 'uuid-deleted' })

    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolverWithRedirect(route, {} as any)
    )

    expect(mockStore.clearIntegrityLink).toHaveBeenCalled()
    expect(result).toBeInstanceOf(RedirectCommand)
    expect((result as RedirectCommand).redirectTo).toEqual(
      router.parseUrl('/import')
    )
  })

  it('should return RedirectCommand to /import on 403', async () => {
    mockStore.loadIntegrityLink = vi.fn().mockRejectedValue({ status: 403 })
    const route = makeRoute({ intlink_id: 'uuid-forbidden' })

    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolverWithRedirect(route, {} as any)
    )

    expect(result).toBeInstanceOf(RedirectCommand)
  })

  it('should return RedirectCommand to /import on server error', async () => {
    mockStore.loadIntegrityLink = vi.fn().mockRejectedValue({ status: 500 })
    const route = makeRoute({ intlink_id: 'uuid-error' })

    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolverWithRedirect(route, {} as any)
    )

    expect(result).toBeInstanceOf(RedirectCommand)
  })

  it('should return the loaded integrity link on success', async () => {
    const route = makeRoute({ intlink_id: 'uuid-1' })

    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolverWithRedirect(route, {} as any)
    )

    expect(result).toEqual({ id: 'uuid-1' })
  })

  it('should clear store and return undefined when no intlink_id', async () => {
    const route = makeRoute()
    const result = await TestBed.runInInjectionContext(() =>
      IntegrityLinkResolverWithRedirect(route, {} as any)
    )

    expect(mockStore.clearIntegrityLink).toHaveBeenCalled()
    expect(result).toBeUndefined()
  })
})
