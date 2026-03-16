import { inject } from '@angular/core'
import { ActivatedRouteSnapshot, RedirectCommand, ResolveFn, Router } from '@angular/router'
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

export const IntegrityLinkResolverWithRedirect = createIntegrityLinkResolver('/import')
