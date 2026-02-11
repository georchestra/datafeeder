import { Route } from '@angular/router'
import { MainLayoutComponent } from './layout/main-layout.component'

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
          )
      },
      {
        path: ':intlink_id',
        loadComponent: () =>
          import('./layout/intlink-layout.component').then(
            (m) => m.IntlinkLayoutComponent
          ),
        children: [
          {
            path: 'edit',
            loadComponent: () =>
              import('./features/metadata/metadata.component').then(
                (m) => m.MetadataComponent
              )
          },
          {
            path: 'events',
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
