{{/*
Expand the name of the chart.
*/}}
{{- define "agent-studio.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this.
*/}}
{{- define "agent-studio.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "agent-studio.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "agent-studio.labels" -}}
helm.sh/chart: {{ include "agent-studio.chart" . }}
{{ include "agent-studio.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "agent-studio.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agent-studio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Postgres service name
*/}}
{{- define "agent-studio.postgres.fullname" -}}
{{- printf "%s-postgres" (include "agent-studio.fullname" .) }}
{{- end }}

{{/*
Redis service name
*/}}
{{- define "agent-studio.redis.fullname" -}}
{{- printf "%s-redis" (include "agent-studio.fullname" .) }}
{{- end }}

{{/*
Backend service name
*/}}
{{- define "agent-studio.backend.fullname" -}}
{{- printf "%s-backend" (include "agent-studio.fullname" .) }}
{{- end }}

{{/*
Backend image
*/}}
{{- define "agent-studio.backend.image" -}}
{{- $registry := .Values.global.acrRegistry }}
{{- if .Values.backend.image.repository }}
{{- printf "%s:%s" .Values.backend.image.repository .Values.backend.image.tag }}
{{- else }}
{{- printf "%s/backend:%s" $registry .Values.backend.image.tag }}
{{- end }}
{{- end }}

{{/*
Frontend image
*/}}
{{- define "agent-studio.frontend.image" -}}
{{- $registry := .Values.global.acrRegistry }}
{{- if .Values.frontend.image.repository }}
{{- printf "%s:%s" .Values.frontend.image.repository .Values.frontend.image.tag }}
{{- else }}
{{- printf "%s/frontend:%s" $registry .Values.frontend.image.tag }}
{{- end }}
{{- end }}

{{/*
Database URL constructed from postgres values
*/}}
{{- define "agent-studio.databaseUrl" -}}
{{- $user := .Values.postgres.user }}
{{- $password := .Values.postgres.password }}
{{- $host := include "agent-studio.postgres.fullname" . }}
{{- $port := .Values.postgres.port | toString }}
{{- $db := .Values.postgres.db }}
{{- printf "postgresql+asyncpg://%s:%s@%s:%s/%s" $user $password $host $port $db }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "agent-studio.redisUrl" -}}
{{- $host := include "agent-studio.redis.fullname" . }}
{{- printf "redis://%s:6379/0" $host }}
{{- end }}

{{/*
Checkpointer DSN
*/}}
{{- define "agent-studio.checkpointerDsn" -}}
{{- $user := .Values.postgres.user }}
{{- $password := .Values.postgres.password }}
{{- $host := include "agent-studio.postgres.fullname" . }}
{{- $db := .Values.postgres.db }}
{{- printf "postgresql://%s:%s@%s:5432/%s" $user $password $host $db }}
{{- end }}
