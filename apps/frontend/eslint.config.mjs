import js from '@eslint/js'
import angular from 'angular-eslint'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: [
      '**/dist',
      '**/vitest.config.*.timestamp*',
      '**/node_modules',
      '**/.angular',
      'src/app/core/api/**'
    ]
  },
  js.configs.recommended,
  ...angular.configs.tsRecommended,
  {
    files: ['**/*.ts'],
    ignores: ['**/*.spec.ts', '**/test-setup.ts'],
    languageOptions: {
      globals: {
        console: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        window: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        Blob: 'readonly',
        URL: 'readonly',
        FileReader: 'readonly',
        navigator: 'readonly',
        MouseEvent: 'readonly',
        Event: 'readonly',
        HTMLElement: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLSelectElement: 'readonly'
      }
    },
    rules: {
      '@angular-eslint/directive-selector': [
        'error',
        {
          type: 'attribute',
          prefix: 'app',
          style: 'camelCase'
        }
      ],
      '@angular-eslint/component-selector': [
        'error',
        {
          type: 'element',
          prefix: 'app',
          style: 'kebab-case'
        }
      ]
    }
  },
  {
    files: ['**/*.html'],
    ...angular.configs.templateRecommended[0]
  },
  {
    files: ['**/*.html'],
    ...angular.configs.templateAccessibility[0]
  }
)
