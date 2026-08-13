{{/* Common labels applied to every object. */}}
{{- define "agentic.labels" -}}
app.kubernetes.io/part-of: agentic-ai-os
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
