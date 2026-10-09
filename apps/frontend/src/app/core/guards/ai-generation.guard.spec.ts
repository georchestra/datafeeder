import { TestBed } from '@angular/core/testing'
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router'
import { MatDialog } from '@angular/material/dialog'
import { TranslateModule } from '@ngx-translate/core'
import { of } from 'rxjs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AiGenerationStore } from '../stores/ai-generation.store'
import { confirmLeaveDuringAiGenerationGuard } from './ai-generation.guard'

describe('confirmLeaveDuringAiGenerationGuard', () => {
  let aiGenerationStore: AiGenerationStore
  let mockMatDialog: { open: ReturnType<typeof vi.fn> }

  const runGuard = (intlinkId: string) =>
    TestBed.runInInjectionContext(() =>
      confirmLeaveDuringAiGenerationGuard(
        {},
        {
          params: { intlink_id: intlinkId }
        } as unknown as ActivatedRouteSnapshot,
        {} as RouterStateSnapshot,
        {} as RouterStateSnapshot
      )
    )

  beforeEach(() => {
    mockMatDialog = {
      open: vi.fn().mockReturnValue({ afterClosed: () => of(true) })
    }
    TestBed.configureTestingModule({
      imports: [TranslateModule.forRoot()],
      providers: [{ provide: MatDialog, useValue: mockMatDialog }]
    })
    aiGenerationStore = TestBed.inject(AiGenerationStore)
  })

  it('should allow leaving when no generation is running', async () => {
    expect(await runGuard('intlink-1')).toBe(true)
    expect(mockMatDialog.open).not.toHaveBeenCalled()
  })

  it('should allow leaving when the generation runs for another record', async () => {
    aiGenerationStore.start('intlink-2')
    expect(await runGuard('intlink-1')).toBe(true)
    expect(mockMatDialog.open).not.toHaveBeenCalled()
  })

  it('should ask for confirmation when the generation runs for the record', async () => {
    aiGenerationStore.start('intlink-1')
    expect(await runGuard('intlink-1')).toBe(true)
    expect(mockMatDialog.open).toHaveBeenCalledOnce()
  })

  it('should stay on the record if the user cancels', async () => {
    mockMatDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) })
    aiGenerationStore.start('intlink-1')
    expect(await runGuard('intlink-1')).toBe(false)
  })

  it('should not ask anymore once the generation is finished', async () => {
    aiGenerationStore.start('intlink-1')
    aiGenerationStore.finish('intlink-1')
    expect(await runGuard('intlink-1')).toBe(true)
    expect(mockMatDialog.open).not.toHaveBeenCalled()
  })
})
