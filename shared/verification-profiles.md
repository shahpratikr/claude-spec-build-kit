# Verification Profiles

Read by build-phase when CLAUDE.md and CI name no test command, and by spec-interview probe DP7. Commands from CLAUDE.md or CI always come first. This table only supplies a recommended option to put in the BLOCKING question.

| Signal | Static checks | Dry-run or tests |
| --- | --- | --- |
| pyproject.toml, pytest.ini | ruff or flake8, mypy | pytest |
| package.json | eslint, tsc --noEmit | npm test |
| .csproj, .sln | dotnet build -warnaserror | dotnet test |
| go.mod, Cargo.toml | go vet, cargo clippy | go test, cargo test |
| pom.xml, build.gradle | mvn verify, gradle check | the same |
| .ps1, .psm1 | Invoke-ScriptAnalyzer | Invoke-Pester |
| .tf | terraform fmt -check, terraform validate, tflint | terraform plan, written to a file |
| .bicep | bicep build, bicep lint | az deployment what-if |
| Chart.yaml, Kubernetes YAML | helm lint, kubeconform | helm template, kubectl diff |
| Dockerfile | hadolint | docker build, when allowed |
| Pipeline YAML | actionlint, yamllint | none |
| .md only | markdownlint, link check | none |
| .sql migrations | sqlfluff | up and down on a scratch database |

## Rules
- A command that changes remote state (apply, deploy, any create or delete against a cloud or a tenant) is never run as verification. Use its read-only form: plan, what-if, diff, template.
- A validation command counts as a test only if its exit code fails when the AC is violated. Output a reader must judge does not count.
- A task with no unit tests is not executable-verified. Say so in the brief and the report, mark the can-fail pass N/A with that reason, and verify each AC with a validation command from this table.
- When no executable check exists at all, say "not executable-verified", record the ACs a reviewer verified by reading, and accept the NEEDS REVIEW verdict that follows.
