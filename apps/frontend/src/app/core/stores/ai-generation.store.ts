import { Injectable, signal } from '@angular/core'

/**
 * Tracks the AI metadata generation in progress, shared between the AI button
 * and the navigation guard warning before leaving the record.
 */
@Injectable({ providedIn: 'root' })
export class AiGenerationStore {
  /** Integrity link whose metadata are being generated, null if none */
  readonly generatingIntlinkId = signal<string | null>(null)

  start(intlinkId: string): void {
    this.generatingIntlinkId.set(intlinkId)
  }

  finish(intlinkId: string): void {
    // A generation started meanwhile on another record must stay tracked
    if (this.generatingIntlinkId() === intlinkId)
      this.generatingIntlinkId.set(null)
  }
}
