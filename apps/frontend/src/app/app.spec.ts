import { TestBed } from '@angular/core/testing'
import { getThemeConfig, ThemeService } from 'geonetwork-ui'
import { vi } from 'vitest'
import { App } from './app'
import { provideRouter } from '@angular/router'
import { appRoutes } from './app.routes'

vi.mock('geonetwork-ui', async (importOriginal) => ({
  ...(await importOriginal<typeof import('geonetwork-ui')>()),
  getThemeConfig: vi.fn()
}))

describe('App', () => {
  beforeEach(async () => {
    vi.spyOn(ThemeService, 'applyCssVariables').mockImplementation(() => {})
    vi.spyOn(ThemeService, 'setFavicon').mockImplementation(() => {})
    vi.mocked(getThemeConfig).mockReturnValue({
      PRIMARY_COLOR: '#111111',
      SECONDARY_COLOR: '#222222',
      MAIN_COLOR: '#333333',
      BACKGROUND_COLOR: '#444444'
    } as ReturnType<typeof getThemeConfig>)
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(appRoutes)]
    }).compileComponents()
  })

  afterEach(() => vi.restoreAllMocks())

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App)
    const app = fixture.componentInstance
    expect(app).toBeTruthy()
  })

  it('applies the theme from the configuration, with default fonts', () => {
    TestBed.createComponent(App)
    expect(ThemeService.applyCssVariables).toHaveBeenCalledWith(
      '#111111',
      '#222222',
      '#333333',
      '#444444',
      'Lato',
      'Lato',
      undefined
    )
    expect(ThemeService.setFavicon).not.toHaveBeenCalled()
  })

  it('applies the configured fonts and favicon', () => {
    vi.mocked(getThemeConfig).mockReturnValue({
      PRIMARY_COLOR: '#111111',
      SECONDARY_COLOR: '#222222',
      MAIN_COLOR: '#333333',
      BACKGROUND_COLOR: '#444444',
      MAIN_FONT: 'Inter',
      TITLE_FONT: 'Petrona',
      FONTS_STYLESHEET_URL: 'https://fonts.example.org/fonts.css',
      FAVICON: 'https://example.org/favicon.ico'
    } as ReturnType<typeof getThemeConfig>)
    TestBed.createComponent(App)
    expect(ThemeService.applyCssVariables).toHaveBeenCalledWith(
      '#111111',
      '#222222',
      '#333333',
      '#444444',
      'Inter',
      'Petrona',
      'https://fonts.example.org/fonts.css'
    )
    expect(ThemeService.setFavicon).toHaveBeenCalledWith(
      'https://example.org/favicon.ico'
    )
  })
})
