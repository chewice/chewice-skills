"""State the current scientific question and upstream input here."""

from pathlib import Path

import TODO_PACKAGE


input_path = Path("inputs/TODO_INPUT")
output_path = Path("derived/TODO_OUTPUT")

# Read the current project object directly; use the project's real library call.
analysis_data = None
print(analysis_data)

# Inspect only the structure or groups needed for the next judgment.
# print(analysis_data.shape)
# print(analysis_data.head())

# Optional when this operation will later be batched: try one representative item first.
representative_id = "TODO_REPRESENTATIVE_ID"
# representative_result = TODO_METHOD(analysis_data, representative_id)
# representative_result

# Optional when the task compares candidates: keep diagnostics visible before choosing.
candidate_values = []
candidate_results = {}

for candidate_value in candidate_values:
    # candidate_results[candidate_value] = TODO_METHOD(
    #     analysis_data,
    #     candidate_value=candidate_value,
    # )
    pass

selected_value = None  # TODO only for a candidate comparison: set after inspection.

# Optional batch extension: extract a per-item helper only after the trial is stable.
# analysis_result = TODO_DOWNSTREAM(analysis_data, selected_value)

# Save only a scientifically useful result or known downstream handoff.
# output_path.parent.mkdir(parents=True, exist_ok=True)
# TODO_WRITE(analysis_result, output_path)

# TODO after execution: record the observed limitation or next question.
