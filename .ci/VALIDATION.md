# Validation — 2026-10-12

Validated the updated workspace against the running Docker SonarQube server. These results describe local validation, not a completed GitHub Actions run.

| Component | Tests passed | SonarQube coverage | Gate | Unresolved issues |
|---|---:|---:|---|---:|
| product-service | 47 | 93.8% | OK | 0 |
| user-service | 39 | 93.9% | OK | 0 |
| media-service | 32 | 92.9% | OK | 0 |
| gateway | 16 | 98.0% | OK | 0 |
| discovery | 2 | 100.0% | OK | 0 |
| frontend | 138 | 91.1% | OK | 0 |

Frontend runner coverage: 93.08% statements, 83.85% branches, 86.59% functions, and 96.03% lines. All four metrics enforce an 80% minimum. The frontend production build passed.

The bootstrap provisioning tests passed (16 tests). Jenkins credentials and Execute Analysis permission were verified for all six projects. Jenkins validated the updated Jenkinsfile. actionlint 1.7.12 validated the GitHub Actions workflow.

A disposable instance started from `.ci/compose.sonar.yml`, initialized its administrator and gate successfully, and analyzed an intentionally uncovered sample. Its scanner exited nonzero and the coverage gate reported ERROR at 0.0%. The validation stack was removed afterward.

Persistent projects use Buy01 Quality Gate, including 80% overall and new-code coverage, zero overall code smells/bugs/vulnerabilities and zero new issues. No issue suppressions or false-positive transitions were used to achieve these results.

GitHub still rejects protected branches on this private repository’s current plan. The prepared branch-protection JSON cannot enforce merges until the repository has a qualifying plan or the owner explicitly authorizes public visibility. Credentials removed from production defaults still require rotation at their provider.
