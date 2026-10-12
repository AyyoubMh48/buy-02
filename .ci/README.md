# Code quality and review workflow

GitHub Actions runs `Code quality / Tests and SonarQube gates` on every branch push, pull request, daily at 02:17 UTC, and manual dispatch. The workflow uses fresh GitHub-hosted runners, pinned actions, Docker SonarQube plus PostgreSQL, Java 21, and Node 24. It does not use production credentials or deploy the application.

Community Build does not offer native PR decoration or branch analysis. Each Actions run therefore scans all six projects in its own isolated Docker SonarQube server. PR runs scan GitHub's proposed merge commit; branch pushes scan the pushed commit. No PR scan can overwrite the persistent `main` dashboard. This is whole-code validation, not native PR differential analysis. After each run the temporary server is removed. Its metrics, issues, gate results, JaCoCo reports, and frontend HTML/LCOV reports remain in the `quality-<run>-<attempt>` artifact for 30 days. A table is visible in the Actions job summary.

The persistent SonarQube dashboard at http://localhost:9000 retains Jenkins `main` analysis history. Jenkins has a nightly scan trigger too; timer-triggered runs skip deployment. Coverage reports are archived on every Jenkins build.

`Buy01 Quality Gate` preserves Sonar way's new-code rules: zero new issues, at least 80% new-code coverage, at most 3% new-code duplication, and 100% reviewed new security hotspots. It additionally requires zero bugs, vulnerabilities, and code smells and at least 80% coverage across the whole project. The small-change coverage bypass is disabled. Backend coverage is enforced on both all code and new code. Frontend coverage also requires at least 80% statements, branches, functions, and lines across all application TypeScript files, including files not imported by tests. HTML templates are checked by SonarQube's HTML profile; compiled template counters are not included in the TypeScript coverage percentage.

## Required review and merge protection

1. Activate the Actions workflow by committing and pushing it with the changes.
2. Keep `main` changes in pull requests. Resolve all issues introduced by the change. Document a false positive with a SonarQube issue link, concrete evidence, and an independent reviewer's approval. Do not dismiss findings simply to make a gate pass.
3. Once a qualifying GitHub plan is available (or after an explicitly authorized change to public visibility), apply the prepared rule:

   ```sh
   gh api --method PUT repos/anasbaip/safe-zone/branches/main/protection --input .ci/main-protection.json
   ```

   This requires the quality check, an up-to-date branch, one independent approval of the latest push, resolved conversations, and applies to administrators. Force pushes and branch deletion are disabled. GitHub currently rejects protected branches on this private repository's plan; the JSON file alone does not enforce merges.
4. Compare coverage, duplication, reliability, maintainability, and security metrics in the persistent SonarQube activity view and saved CI artifacts. Review the scheduled result daily.

## Local verification

```sh
cd frontend
npm ci
npm run test:coverage
npm run build
```

Run `bash ./mvnw -B clean verify` in each backend directory with Java 21. Production requires `JWT_SECRET` and Cloudinary variables; application context tests use explicit non-production fixtures. Supply a test JWT secret for gateway context tests.

For a full scan of an existing local server, build coverage first, install the pinned SonarScanner CLI, then run `SONAR_HOST_URL=http://localhost:9000 python3 .ci/sonar_ci.py` with `SONAR_TOKEN` supplied securely in the environment as an administrator User Token. The script provisions temporary project-scoped analysis tokens, revokes only those temporary tokens when finished, scans all services, writes `reports/quality/`, and exits nonzero for any scanner or gate failure. `--initialize` is exclusively for a fresh disposable server using its initial admin account; never use it against the persistent instance.

Cloudinary credentials previously appeared in application defaults. They have been removed from current source, but must be rotated at the provider because repository history may still contain them. Neither CI fixture values nor report artifacts are production secrets.
