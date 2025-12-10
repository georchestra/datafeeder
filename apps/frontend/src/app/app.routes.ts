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
          import('./features/home/home.component').then((m) => m.HomeComponent)
      },
      {
        path: 'import',
        loadComponent: () =>
          import('./features/import/import.component').then(
            (m) => m.ImportComponent
          )
      },
      {
        path: 'events/:reference',
        loadComponent: () =>
          import('./features/events/events.component').then(
            (m) => m.EventsComponent
          )
      }
    ]
  }
]
