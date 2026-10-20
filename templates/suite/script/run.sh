#!/bin/sh
# A DTP test runner in plain sh. The engine calls:
#   run.sh --list            -> print one "discover" event per test
#   run.sh --run ID [ID...]  -> run those tests, print start/assert/end events
# Events are JSON lines written to the file descriptor $DT_REPORT_FD.
# $DT_PROJECT is the isolated copy of the student's project.

out() { printf '%s\n' "$1" >&"${DT_REPORT_FD:-1}"; }
esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }   # JSON-escape one line

TESTS="has_makefile has_readme"
desc() {
	case "$1" in
		has_makefile) echo "The project has a Makefile" ;;
		has_readme)   echo "The project has a README.md" ;;
	esac
}
check() { # return 0 when the test passes, print the actual value otherwise
	case "$1" in
		has_makefile) [ -f "$DT_PROJECT/Makefile" ] ;;
		has_readme)   [ -f "$DT_PROJECT/README.md" ] ;;
	esac
}

out '{"t":"hello","protocol":1,"harness":"sh"}'
if [ "$1" = "--list" ]; then
	for t in $TESTS; do
		out "{\"t\":\"discover\",\"id\":\"files/$t\",\"name\":\"$t\",\"desc\":\"$(esc "$(desc "$t")")\"}"
	done
	exit 0
fi
[ "$1" = "--run" ] && shift
for id in "${@:-}"; do
	t=${id#files/}
	out "{\"t\":\"start\",\"id\":\"$id\"}"
	if check "$t"; then
		out "{\"t\":\"end\",\"id\":\"$id\",\"status\":\"pass\"}"
	else
		out "{\"t\":\"assert\",\"id\":\"$id\",\"ok\":false,\"msg\":\"$(esc "$(desc "$t")")\",\"expected\":\"present\",\"actual\":\"missing\"}"
		out "{\"t\":\"end\",\"id\":\"$id\",\"status\":\"fail\"}"
	fi
done
out '{"t":"done"}'
