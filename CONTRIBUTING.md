<!--
SPDX-FileCopyrightText: 2023 Bundesministerium des Innern und für Heimat, PG ZenDiS "Projektgruppe für Aufbau ZenDiS"
SPDX-License-Identifier: Apache-2.0
-->

# Contributing to openDesk Edu

Thanks for your interest in contributing! Please read the [project's workflow documentation](./docs/developer/workflow.md)
for standards like commit messages and branching conventions.

## Helm vs. Operators vs. Manifests

Due to DVS requirements:

- we have to use [Helm charts](https://helm.sh/) (that can consist of Manifests).
- we should avoid stand-alone Manifests.
- we do not use Operators and CRDs.

In order to align the Helm files from various sources into the unified deployment of openDesk we make use of
[Helmfile](https://github.com/helmfile/helmfile).

## Educational Services

openDesk Edu adds university-specific services to the openDesk CE platform:

| Category | Services |
|----------|----------|
| Learning Management | ILIAS, Moodle |
| Video Conferencing | BigBlueButton (alternative to Jitsi) |
| File Sync & Share | OpenCloud (alternative to Nextcloud) |
| Groupware | SOGo (alternative to OX App Suite) |
| Collaborative Editing | Etherpad |
| Knowledge Base | BookStack |
| Project Boards | Planka |
| Helpdesk | Zammad |
| Surveys | LimeSurvey |
| Whiteboarding | Excalidraw |
| Diagramming | Draw.io |
| Password Management | Self-Service Password |

### Adding a new chart

When contributing a new education service, ensure the following are present:

1. **Helm chart**: `helmfile/charts/<service>/` with `Chart.yaml`, `values.yaml`, `templates/`
2. **CI values**: `helmfile/charts/<service>/ci/ci-values.yaml` for chart-testing
3. **Unit tests**: `helmfile/charts/<service>/tests/` with `*_test.yaml` (helm-unittest)
4. **Helmfile app config**: `helmfile/apps/<service>/helmfile-child.yaml.gotmpl` + `values.yaml.gotmpl`
5. **Portal tile**: Entry in `helmfile/apps/nubus/values-nubus.yaml.gotmpl` (UDM YAML)
6. **Portal icon**: SVG at `helmfile/files/theme/edu_services/<service>.svg` (111x111px)
7. **External services doc**: Database/cache config in `docs/external-services.md`
8. **CI integration**: Chart added to `.github/workflows/lint.yaml` matrix

All charts must pass `helm lint`, `helm template`, and `helm-unittest` before merging.

## Tooling

New tools should not be introduced without first discussing it with the team. We should avoid adding unnecessary complexity.

## In doubt? Ask!

When in doubt please [open an issue](https://github.com/tobias-weiss-ai-xr/opendesk-edu/issues) and start a discussion.
