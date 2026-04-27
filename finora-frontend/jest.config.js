const nextJest = require("next/jest");

const createJestConfig = nextJest({
  dir: "./",
});

/** @type {import('jest').Config} */
const config = {
  testEnvironment: "node",
  // roots controls where Jest scans — must include the external test dir
  roots: ["<rootDir>/../tests/frontend"],
  testMatch: ["**/*.test.ts", "**/*.test.tsx"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  // Suppress Haste collision from .next/standalone build artifact
  modulePathIgnorePatterns: ["<rootDir>/.next/standalone"],
};

module.exports = createJestConfig(config);
