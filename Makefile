PYS	= ./pys

help:
	@echo 'Targets:'
	@echo '* qa - check code quality'

qa:
	if [ ! -f .secrets ] ; then $(PYS) detect-secrets scan | tee .secrets | jq .results ; fi
	$(PYS) detect-secrets audit .secrets
	$(PYS) ruff check
	$(PYS) cyclo scullery

