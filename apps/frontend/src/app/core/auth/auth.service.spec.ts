import { TestBed } from '@angular/core/testing'
import { AuthService } from './auth.service'
import { LoginCredentials } from './auth.model'

describe('AuthService', () => {
  let service: AuthService

  beforeEach(() => {
    TestBed.configureTestingModule({})
    service = TestBed.inject(AuthService)
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('should be created', () => {
    expect(service).toBeTruthy()
  })

  describe('initial state', () => {
    it('should not be authenticated initially', () => {
      expect(service.isAuthenticated()).toBe(false)
    })

    it('should have no user initially', () => {
      expect(service.getUser()).toBeNull()
    })

    it('should have no token initially', () => {
      expect(service.getToken()).toBeNull()
    })
  })

  describe('login', () => {
    it('should login successfully with valid credentials', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      const user = await service.login(credentials)

      expect(user).toBeTruthy()
      expect(user.username).toBe('testuser')
      expect(service.isAuthenticated()).toBe(true)
    })

    it('should set user after successful login', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      await service.login(credentials)
      const user = service.getUser()

      expect(user).toBeTruthy()
      expect(user?.username).toBe('testuser')
      expect(user?.email).toBe('testuser@example.com')
    })

    it('should set token after successful login', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      await service.login(credentials)
      const token = service.getToken()

      expect(token).toBeTruthy()
      expect(token).toBe('mock-access-token')
    })

    it('should persist auth state to localStorage', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      await service.login(credentials)
      const stored = localStorage.getItem('datafeeder_auth')

      expect(stored).toBeTruthy()
      const state = JSON.parse(stored!)
      expect(state.isAuthenticated).toBe(true)
      expect(state.user.username).toBe('testuser')
    })

    it('should reject with invalid credentials', async () => {
      const credentials: LoginCredentials = {
        username: '',
        password: ''
      }

      try {
        await service.login(credentials)
        throw new Error('Expected login to reject')
      } catch (error) {
        expect((error as Error).message).toBe('Invalid credentials')
      }
      expect(service.isAuthenticated()).toBe(false)
    })
  })

  describe('logout', () => {
    it('should clear authentication state', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      await service.login(credentials)
      expect(service.isAuthenticated()).toBe(true)

      service.logout()

      expect(service.isAuthenticated()).toBe(false)
      expect(service.getUser()).toBeNull()
      expect(service.getToken()).toBeNull()
    })

    it('should remove auth state from localStorage', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      await service.login(credentials)
      expect(localStorage.getItem('datafeeder_auth')).toBeTruthy()

      service.logout()

      expect(localStorage.getItem('datafeeder_auth')).toBeNull()
    })
  })

  describe('state persistence', () => {
    it('should restore auth state from localStorage', async () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123'
      }

      await service.login(credentials)

      // Create new service instance to test restoration
      const newService = new AuthService()

      expect(newService.isAuthenticated()).toBe(true)
      expect(newService.getUser()?.username).toBe('testuser')
      expect(newService.getToken()).toBe('mock-access-token')
    })

    it('should handle corrupted localStorage data', () => {
      localStorage.setItem('datafeeder_auth', 'invalid-json')

      const newService = new AuthService()

      expect(newService.isAuthenticated()).toBe(false)
      expect(newService.getUser()).toBeNull()
    })
  })
})
