/* ESLint config for `npm run lint`.
 * The repo shipped without any ESLint config, so the lint script failed
 * before checking a single file ("ESLint couldn't find a configuration file").
 * Rule set is the standard Vite React-TS template, tuned to match the
 * codebase's existing idioms (see overrides). */
module.exports = {
  root: true,
  env: { browser: true, es2020: true, node: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', 'node_modules', 'public', '.eslintrc.cjs', '*.config.js', '*.config.ts'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    // HMR ergonomics only (files that export a component plus helpers); not a defect signal.
    'react-refresh/only-export-components': 'off',
    // The codebase predates strict typing (378+ pre-existing tsc errors is the
    // documented baseline); these stay off so lint reports real defects only.
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unused-vars': 'off',
    '@typescript-eslint/no-non-null-assertion': 'off',
    '@typescript-eslint/ban-ts-comment': 'off',
    'no-empty': ['error', { allowEmptyCatch: true }],
  },
}
