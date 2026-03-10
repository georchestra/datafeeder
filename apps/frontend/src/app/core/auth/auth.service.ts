import { Injectable, signal } from '@angular/core'
import { AuthState, LoginCredentials, User, AuthToken } from './auth.model'

const STORAGE_KEY = 'datafeeder_auth'

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private authState = signal<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false
  })

  readonly currentUser = this.authState.asReadonly()

  constructor() {
    this.loadAuthState()
  }

  login(credentials: LoginCredentials): Promise<User> {
    // TODO: Implement actual API call
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (credentials.username && credentials.password) {
          const user: User = {
            id: '1',
            username: credentials.username,
            email: `${credentials.username}@example.com`,
            roles: ['user']
          }

          const token: AuthToken = {
            accessToken: 'mock-access-token',
            refreshToken: 'mock-refresh-token',
            expiresIn: 3600
          }

          this.setAuthState(user, token)
          resolve(user)
        } else {
          reject(new Error('Invalid credentials'))
        }
      }, 100)
    })
  }

  logout(): void {
    this.clearAuthState()
  }

  isAuthenticated(): boolean {
    return this.authState().isAuthenticated
  }

  getUser(): User | null {
    return this.authState().user
  }

  getToken(): string | null {
    return this.authState().token?.accessToken || null
  }

  private setAuthState(user: User, token: AuthToken): void {
    const state: AuthState = {
      user,
      token,
      isAuthenticated: true
    }
    this.authState.set(state)
    this.saveAuthState(state)
  }

  private clearAuthState(): void {
    const state: AuthState = {
      user: null,
      token: null,
      isAuthenticated: false
    }
    this.authState.set(state)
    localStorage.removeItem(STORAGE_KEY)
  }

  private saveAuthState(state: AuthState): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }

  private loadAuthState(): void {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        const state = JSON.parse(stored) as AuthState
        this.authState.set(state)
      } catch (error) {
        console.error('Failed to load auth state:', error)
        this.clearAuthState()
      }
    }
  }
}
