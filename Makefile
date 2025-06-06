# Dependency Management
.PHONY: deps-analyze deps-conflicts deps-graph deps-update

deps-analyze:
	python scripts/manage_deps.py --analyze

deps-conflicts:
	python scripts/manage_deps.py --conflicts

deps-graph:
	python scripts/manage_deps.py --graph deps.dot
	dot -Tpng deps.dot -o deps.png

deps-update:
	python scripts/manage_deps.py --update requirements/base.txt
	python scripts/manage_deps.py --update requirements/ml.txt
	python scripts/manage_deps.py --update requirements/prod.txt
	python scripts/manage_deps.py --update requirements/dev.txt 