.PHONY: build check draft clean

build:
	python3 build.py

check:
	cd outreach && python3 render.py --check

draft:
	cd outreach && python3 render.py

evidence:
	python3 sync_evidence.py && python3 build.py

clean:
	rm -rf docs README.md outbox/*
