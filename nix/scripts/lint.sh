
# Static checks on the workflow file: actionlint for the YAML, expressions and action inputs, with shellcheck on every run: block.

log "actionlint $workflow"
actionlint -color "$workflow"
printf 'ok\n'
