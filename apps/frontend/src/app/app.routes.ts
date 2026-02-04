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
        path: 'edit/:intlink_id',
        loadComponent: () =>
          import('./features/metadata/metadata.component').then(
            (m) => m.MetadataComponent
          )
      },
      {
        path: 'events/:intlink_id',
        loadComponent: () =>
          import('./features/events/events.component').then(
            (m) => m.EventsComponent
          )
      }
    ]
  }
]
