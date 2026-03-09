import { inject } from '@angular/core'
import { ActivatedRouteSnapshot, ResolveFn } from '@angular/router'
import { IntegrityLinkStore } from '../stores/integrity-link.store'
import { IntegrityLinkResponse } from '../api/models'

export const IntegrityLinkResolver: ResolveFn<
  IntegrityLinkResponse | undefined
> = async (route: ActivatedRouteSnapshot) => {
  const integrityLinkStore = inject(IntegrityLinkStore)

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
      return undefined
    }
  }

  console.log(
    'No intlink_id provided in route parameters. Clearing integrity link store.'
  )

  integrityLinkStore.clearIntegrityLink()

  return undefined
}
