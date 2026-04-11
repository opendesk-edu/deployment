# SPDX-FileCopyrightText: 2026 openDesk Edu Contributors
# SPDX-License-Identifier: Apache-2.0
{{/*
Expand the name of the release.
*/}}
{{- define "hisinone-proxy.name" -}}
{{-   default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "hisinone-proxy.labels" -}}
app.kubernetes.io/name: {{ include "hisinone-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{-   if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{-   end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "hisinone-proxy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hisinone-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
DB Host generator
*/}}
{{- define "hisinone-proxy.postgresql.host" -}}
{{- .Release.Name }}-postgresql
{{- end -}}

{{/*
DB Username generator
*/}}
{{- define "hisinone-proxy.postgresql.username" -}}
{{- .Values.postgresql.auth.username -}}
{{- end -}}

{{/*
DB Password generator
*/}}
{{- define "hisinone-proxy.postgresql.password" -}}
{{- .Values.postgresql.auth.password -}}
{{- end -}}

{{/*
DB Name generator
*/}}
{{- define "hisinone-proxy.postgresql.database" -}}
{{- .Values.postgresql.auth.database -}}
{{- end -}}

{{/*
Fullname generator
*/}}
{{- define "hisinone-proxy.fullname" -}}
{{- .Release.Name }}-hisinone-proxy
{{- end -}}

{{/*
PostgreSQL fullname generator
*/}}
{{- define "hisinone-proxy.postgresql.fullname" -}}
{{- .Release.Name }}-postgresql
{{- end -}}