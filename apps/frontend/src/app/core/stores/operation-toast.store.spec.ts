import { TestBed } from '@angular/core/testing'
import { HttpErrorResponse } from '@angular/common/http'
import { OperationToastStore } from './operation-toast.store'

describe('OperationToastStore', () => {
  let store: OperationToastStore

  beforeEach(() => {
    TestBed.configureTestingModule({})
    store = TestBed.inject(OperationToastStore)
  })

  it('should start with no toasts', () => {
    expect(store.toasts()).toHaveLength(0)
  })

  it('should add an error toast with the default translation key', () => {
    store.addError('metadataSave')
    expect(store.toasts()).toHaveLength(1)
    expect(store.toasts()[0].translationKey).toBe(
      'errors.operation.metadataSave'
    )
    expect(store.toasts()[0].type).toBe('error')
  })

  it('should use error.error.detail as translation key when present', () => {
    const error = new HttpErrorResponse({
      error: { detail: 'some.backend.key' },
      status: 400
    })
    store.addError('metadataSave', error)
    expect(store.toasts()[0].translationKey).toBe('some.backend.key')
  })

  it('should fall back to default key when error.error.detail is not a string', () => {
    const error = new HttpErrorResponse({
      error: { detail: 42 },
      status: 400
    })
    store.addError('metadataSave', error)
    expect(store.toasts()[0].translationKey).toBe(
      'errors.operation.metadataSave'
    )
  })

  it('should fall back to default key when error is not an HttpErrorResponse', () => {
    store.addError('deletion', new Error('network error'))
    expect(store.toasts()[0].translationKey).toBe('errors.operation.deletion')
  })

  it('should add an info toast with the info translation key', () => {
    store.addInfo('recurrenceUpdate')
    expect(store.toasts()).toHaveLength(1)
    expect(store.toasts()[0].translationKey).toBe(
      'info.operation.recurrenceUpdate'
    )
    expect(store.toasts()[0].type).toBe('info')
  })

  it('should stack toasts with most recent last', () => {
    store.addError('gnPublish')
    store.addError('gnUnpublish')
    expect(store.toasts()).toHaveLength(2)
    expect(store.toasts()[0].translationKey).toBe('errors.operation.gnPublish')
    expect(store.toasts()[1].translationKey).toBe(
      'errors.operation.gnUnpublish'
    )
  })

  it('should remove a toast by id', () => {
    store.addError('gnPublish')
    store.addError('gnUnpublish')
    const id = store.toasts()[0].id
    store.remove(id)
    expect(store.toasts()).toHaveLength(1)
    expect(store.toasts()[0].translationKey).toBe(
      'errors.operation.gnUnpublish'
    )
  })

  it('should only remove the targeted toast', () => {
    store.addError('gnPublish')
    store.addError('gnUnpublish')
    store.addError('deletion')
    const idToRemove = store.toasts()[1].id
    store.remove(idToRemove)
    expect(store.toasts()).toHaveLength(2)
    expect(store.toasts()[0].translationKey).toBe('errors.operation.gnPublish')
    expect(store.toasts()[1].translationKey).toBe('errors.operation.deletion')
  })

  it('should assign a unique id to each toast', () => {
    store.addError('gnPublish')
    store.addError('gnPublish')
    const ids = store.toasts().map((t) => t.id)
    expect(new Set(ids).size).toBe(2)
  })
})
