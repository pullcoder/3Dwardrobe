import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import hooks from 'eslint-plugin-react-hooks'
import a11y from 'eslint-plugin-jsx-a11y'
import globals from 'globals'

export default tseslint.config(
  { ignores: ['dist', 'test-results', 'playwright-report', 'public/mediapipe'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { files: ['**/*.{ts,tsx}'], languageOptions: { globals: globals.browser },
    plugins: { 'react-hooks': hooks, 'jsx-a11y': a11y },
    rules: { ...hooks.configs.recommended.rules, ...a11y.configs.recommended.rules } },
  { files: ['*.{js,ts}', 'e2e/*.ts'], languageOptions: { globals: globals.node } },
  { files: ['scripts/*.mjs'], languageOptions: { globals: globals.node } },
  { files: ['public/pose-worker.js'], languageOptions: { globals: globals.worker } },
)
