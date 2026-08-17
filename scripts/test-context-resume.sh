#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
required='AGENTS.md AGY.md README.md CHANGELOG.md docs/development.md docs/project-journal.md'

for path in $required; do
  test -f "$root/$path" || { echo "missing: $path" >&2; exit 1; }
done

assert_contains() {
  pattern=$1
  path=$2
  grep -Eqi "$pattern" "$root/$path" || {
    echo "missing context pattern '$pattern' in $path" >&2
    exit 1
  }
}

assert_contains 'project brain' AGENTS.md
assert_contains 'Luna' AGENTS.md
assert_contains 'approval' AGENTS.md
assert_contains 'Routine.*Terra low' AGENTS.md
assert_contains 'Standard.*Terra medium' AGENTS.md
assert_contains 'disjoint (write scopes|path ownership|paths)' AGENTS.md
assert_contains 'acceptance criteria' AGENTS.md
assert_contains 'local-only' AGENTS.md
assert_contains 'AGY ONLY' AGY.md
assert_contains 'invoke_subagent' AGY.md
assert_contains 'Purpose' README.md
assert_contains 'Capabilities' README.md
assert_contains 'System architecture' README.md
assert_contains 'Cloud resources' README.md
assert_contains 'deployed' README.md
assert_contains 'planned' README.md
assert_contains 'Current resume point' docs/project-journal.md

echo "Project context smoke test passed."
