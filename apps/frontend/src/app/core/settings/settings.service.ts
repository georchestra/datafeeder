import { Injectable, inject, signal } from '@angular/core'
import { getSettingsSettingsGet } from '../api/fn/settings/get-settings-settings-get'
import { Api } from '../api/api'

export interface ProjectionSetting {
  value: string
  label: string
}

export interface AppSettings {
  projections?: ProjectionSetting[]
  enabled_features?: string[]
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private readonly api = inject(Api)

  private settings = signal<AppSettings | null>(null)
  private loading = signal<boolean>(false)
  private error = signal<string | null>(null)

  private readonly defaultProjections: ProjectionSetting[] = [
    { value: 'EPSG:4326', label: 'WGS 84' },
    { value: 'EPSG:3857', label: 'Web Mercator' }
  ]

  readonly currentSettings = this.settings.asReadonly()
  readonly isLoading = this.loading.asReadonly()
  readonly errorMessage = this.error.asReadonly()

  private mergeProjections(
    backendProjections?: ProjectionSetting[]
  ): ProjectionSetting[] {
    const projectionMap = new Map<string, ProjectionSetting>()

    // Add defaults first
    this.defaultProjections.forEach((p) => projectionMap.set(p.value, p))

    // Override/add backend projections
    backendProjections?.forEach((p) => projectionMap.set(p.value, p))

    return Array.from(projectionMap.values())
  }

  async loadSettings(): Promise<AppSettings> {
    if (this.settings()) {
      return Promise.resolve(this.settings()!)
    }

    if (this.loading()) {
      return new Promise((resolve, reject) => {
        const checkInterval = setInterval(() => {
          if (!this.loading()) {
            clearInterval(checkInterval)
            const settings = this.settings()
            if (settings) {
              resolve(settings)
            } else {
              reject(new Error(this.error() || 'Failed to load settings'))
            }
          }
        }, 100)
      })
    }

    this.loading.set(true)
    this.error.set(null)

    let result: AppSettings

    try {
      const backendSettings = await this.api.invoke(getSettingsSettingsGet)
      result = {
        ...backendSettings,
        projections: this.mergeProjections(backendSettings.projections)
      }
      this.settings.set(result)
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to load settings'
      this.error.set(errorMsg)

      // Set default settings on error
      result = {
        projections: this.defaultProjections
      }
      this.settings.set(result)
    } finally {
      this.loading.set(false)
    }

    return result
  }

  getProjections(): ProjectionSetting[] {
    return this.settings()?.projections || []
  }

  getSetting<T>(key: string): T | undefined {
    return this.settings()?.[key] as T | undefined
  }

  reload(): Promise<AppSettings> {
    this.settings.set(null)
    return this.loadSettings()
  }
}
