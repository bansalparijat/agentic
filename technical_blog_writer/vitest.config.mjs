import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/vitest/**/*.test.mjs'],
    environment: 'node',
    fileParallelism: false,
    maxWorkers: 1,
    testTimeout: 10_000,
  },
});
