# R01 端到端验收（T10）。Windows 无 make 时直接 `python run_tests.py` 等价。
.PHONY: test smoke harness

test:
	python run_tests.py

smoke:
	python run_tests.py --no-fail

harness:
	python harness.py verify --brief examples/brief.json --card examples/decision_card.json
