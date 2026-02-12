import type { Config } from 'jest';

const config: Config = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/setup-jest.ts'],
  testPathIgnorePatterns: ['/node_modules/', '/e2e/'],
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.spec.ts', '!src/main.ts', '!src/**/*.module.ts'],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'cobertura'],
  reporters: [
    'default',
    ...(process.env['CI']
      ? [['jest-junit', { outputDirectory: 'test-results', outputName: 'junit.xml' }] as [string, Record<string, string>]]
      : []),
  ],
};

export default config;
