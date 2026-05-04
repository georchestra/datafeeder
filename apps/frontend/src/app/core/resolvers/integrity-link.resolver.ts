import { inject } from '@angular/core'
import {
  ActivatedRouteSnapshot,
  CanActivateFn,
  RedirectCommand,
  ResolveFn,
  Router
} from '@angular/router'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import { IntegrityLinkResponse } from '../api/models'

function createIntegrityLinkResolver(
  redirectOnError?: string
): ResolveFn<IntegrityLinkResponse | RedirectCommand | undefined> {
  return async (route: ActivatedRouteSnapshot) => {
    const integrityLinkStore = inject(IntegrityLinkStore)
    const router = redirectOnError ? inject(Router) : null

    // Get intlink_id from route params or parent route params
    // eg. import/uuid or uuid/edit (here, parent)
    const intlinkId =
      route.params['intlink_id'] || route.parent?.params['intlink_id']

    if (intlinkId) {
      try {
        return await integrityLinkStore.loadIntegrityLink(intlinkId)
      } catch (error) {
        console.error('Error loading integrity link:', error)
        integrityLinkStore.clearIntegrityLink()
        if (redirectOnError && router) {
          return new RedirectCommand(router.parseUrl(redirectOnError))
        }
        return undefined
      }
    }

    console.log(
      'No intlink_id provided in route parameters. Clearing integrity link store.'
    )

    integrityLinkStore.clearIntegrityLink()

    return undefined
  }
}

export const IntegrityLinkResolver = createIntegrityLinkResolver()

export const IntegrityLinkResolverWithRedirect =
  createIntegrityLinkResolver('/import')

/**
 * Blocks navigation to routes unavailable for empty datasets.
 *
 * Safety: Angular Router fully resolves a parent route (all resolvers) before
 * running canActivate guards on child routes. The `events` route is a child of
 * `:intlink_id`, whose resolver populates IntegrityLinkStore — so the guard
 * always sees an up-to-date store value.
 *
 * Redirect encodes the reason as ?unavailable=1 so the layout shell (already
 * mounted as a parent component) can react via its queryParamMap subscription,
 * instead of relying on store state that gets overwritten by the parent resolver
 * on the subsequent navigation back to /edit.
 */
export const rejectEmptyDatasetGuard: CanActivateFn = (route) => {
  const store = inject(IntegrityLinkStore)
  const router = inject(Router)

  const intlinkId = route.parent?.params['intlink_id']
  if (!intlinkId) return true

  if (store.isEmptyDataset()) {
    return new RedirectCommand(
      router.parseUrl(`/${intlinkId}/edit?unavailable=1`)
    )
  }

  return true
}
