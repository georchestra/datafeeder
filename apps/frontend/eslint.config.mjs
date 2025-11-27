import js from '@eslint/js';
import angular from 'angular-eslint';
import tseslint from 'typescript-eslint';
import cypress from 'eslint-plugin-cypress';

export default tseslint.config(
  {
    ignores: ['**/dist', '**/vitest.config.*.timestamp*', '**/node_modules', '**/.angular', 'src/app/core/api/**'],
  },
  js.configs.recommended,
  ...angular.configs.tsRecommended,
  {
    files: ['**/*.ts'],
    ignores: ['**/*.spec.ts', '**/test-setup.ts', 'cypress/**/*', 'e2e/**/*'],
    languageOptions: {
      globals: {
        console: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        window: 'readonly',
      },
    },
    rules: {
      '@angular-eslint/directive-selector': [
        'error',
        {
          type: 'attribute',
          prefix: 'app',
          style: 'camelCase',
        },
      ],
      '@angular-eslint/component-selector': [
        'error',
        {
          type: 'element',
          prefix: 'app',
          style: 'kebab-case',
        },
      ],
    },
  },
  {
    files: ['**/*.html'],
    ...angular.configs.templateRecommended[0],
  },
  {
    files: ['**/*.html'],
    ...angular.configs.templateAccessibility[0],
  },
  {
    files: ['cypress/**/*.cy.ts', 'cypress/**/*.cy.js', 'cypress/**/*.ts', 'cypress/**/*.js'],
    plugins: {
      cypress,
    },
    languageOptions: {
      globals: {
        cy: 'readonly',
        Cypress: 'readonly',
        describe: 'readonly',
        context: 'readonly',
        it: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        before: 'readonly',
        after: 'readonly',
        expect: 'readonly',
        assert: 'readonly',
        console: 'readonly',
        require: 'readonly',
        setTimeout: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        __filename: 'readonly',
        __dirname: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
    },
  }
);
