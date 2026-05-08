module.exports = {
  preset: "ts-jest",
  testEnvironment: "jsdom",
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" },
  setupFilesAfterEach: ["<rootDir>/tests/unit/jest.setup.ts"],
  testMatch: ["<rootDir>/tests/unit/**/*.test.(ts|tsx)"],
  collectCoverageFrom: ["src/**/*.{ts,tsx}", "!src/**/*.d.ts"],
  coverageThreshold: {
    global: { branches: 70, functions: 70, lines: 80, statements: 80 },
  },
};
