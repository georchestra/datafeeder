export interface User {
  id: string
  username: string
  email: string
  roles: string[]
}

export interface AuthToken {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthState {
  user: User | null
  token: AuthToken | null
  isAuthenticated: boolean
}
