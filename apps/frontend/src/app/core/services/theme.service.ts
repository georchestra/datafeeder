import { Injectable, signal, effect } from '@angular/core'

export type Theme = 'light' | 'dark'

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private readonly THEME_KEY = 'datakern-theme'

  theme = signal<Theme>(this.getInitialTheme())

  constructor() {
    effect(() => {
      const theme = this.theme()
      document.documentElement.classList.remove('light', 'dark')
      document.documentElement.classList.add(theme)
      localStorage.setItem(this.THEME_KEY, theme)
    })
  }

  toggleTheme(): void {
    this.theme.update((current) => (current === 'light' ? 'dark' : 'light'))
  }

  setTheme(theme: Theme): void {
    this.theme.set(theme)
  }

  private getInitialTheme(): Theme {
    const stored = localStorage.getItem(this.THEME_KEY) as Theme | null
    if (stored && (stored === 'light' || stored === 'dark')) {
      return stored
    }

    // Check system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }

    return 'light'
  }
}
