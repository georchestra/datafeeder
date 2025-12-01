import { Component, inject, signal } from '@angular/core'
import { MatButtonModule } from '@angular/material/button'
import { MatCheckboxModule } from '@angular/material/checkbox'
import { Api } from '../../core/api/api'
import { readVersionVersionGet } from '../../core/api/functions'

@Component({
  selector: 'app-home',
  imports: [MatButtonModule, MatCheckboxModule],
  template: `
    <div class="space-y-4 py-8">
      <h1 class="text-2xl font-bold">DataKern</h1>

      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
        veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
        commodo consequat.
      </p>

      @if (version()) {
      <div class="rounded-lg bg-blue-50 p-4">
        <p class="text-sm font-medium text-blue-900">
          Backend Version: {{ version() }}
        </p>
      </div>
      }

      <div class="flex items-center gap-4">
        <button mat-raised-button color="primary">Click me</button>
      </div>
    </div>
  `
})
export class HomeComponent {
  private api = inject(Api)
  version = signal<string | null>(null)

  constructor() {
    this.loadVersion()
  }

  private async loadVersion() {
    try {
      const response = await this.api.invoke(readVersionVersionGet)
      this.version.set(response.version)
    } catch (error) {
      console.error('Failed to load version:', error)
    }
  }
}
