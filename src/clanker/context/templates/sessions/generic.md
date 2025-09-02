# Clanker Session Context

## Environment Overview
{{clanker_overview}}

## Available Apps
{{available_apps}}

## Development Guidelines
{{cli_patterns}}

{% if app_name != "general" %}
## Working with {{app_name}}
{{app_context}}
{% endif %}

{% if user_request %}
## User Request
{{user_request}}
{% endif %}
