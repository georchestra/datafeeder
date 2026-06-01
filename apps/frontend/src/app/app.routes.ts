import { Route } from '@angular/router'
import { MainLayoutComponent } from './layout/main-layout.component'
import {
  IntegrityLinkResolverWithRedirect,
  IntegrityLinkResolver,
  rejectEmptyDatasetGuard,
  rejectNonRemoteDatasetGuard
} from './core/resolvers/integrity-link.resolver'

export const appRoutes: Route[] = [
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      {
        path: '',
        loadComponent: () =>
          import(
            './features/integrity-link-list/integrity-link-list.component'
          ).then((m) => m.IntegrityLinkListComponent)
      },
      {
        path: 'import',
        loadComponent: () =>
          import('./features/import/import.component').then(
            (m) => m.ImportComponent
          ),
        resolve: {
          integrityLink: IntegrityLinkResolver
        }
      },
      {
        path: 'import/:intlink_id',
        loadComponent: () =>
          import('./features/import/import.component').then(
            (m) => m.ImportComponent
          ),
        resolve: {
          integrityLink: IntegrityLinkResolverWithRedirect
        }
      },
      {
        path: ':intlink_id',
        loadComponent: () =>
          import('./layout/intlink-layout.component').then(
            (m) => m.IntlinkLayoutComponent
          ),
        resolve: {
          integrityLink: IntegrityLinkResolver
        },
        children: [
          {
            path: 'edit',
            loadComponent: () =>
              import('./features/metadata/metadata.component').then(
                (m) => m.MetadataComponent
              )
          },
          {
            path: 'recurrence',
            canActivate: [rejectNonRemoteDatasetGuard],
            loadComponent: () =>
              import('./features/recurrence/recurrence.component').then(
                (m) => m.RecurrenceComponent
              )
          },
          {
            path: 'events',
            canActivate: [rejectEmptyDatasetGuard],
            loadComponent: () =>
              import('./features/events/events.component').then(
                (m) => m.EventsComponent
              )
          },
          {
            path: 'authorizations',
            loadComponent: () =>
              import('./features/authorizations/authorizations.component').then(
                (m) => m.AuthorizationsComponent
              )
          },
          { path: '', redirectTo: 'edit', pathMatch: 'full' }
        ]
      }
    ]
  }
]
