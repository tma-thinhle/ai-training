"""Score saved model judgments. No network calls."""

from pydantic import BaseModel, Field

from app.schemas import MeetingAnalysis


class SemanticMatch(BaseModel):
    model_config = {"extra": "forbid", "strict": True}

    expected_index: int = Field(ge=0)
    predicted_index: int = Field(ge=0)
    reason: str = Field(min_length=1, pattern=r"\S")


class MeetingJudgment(BaseModel):
    model_config = {"extra": "forbid", "strict": True}

    decision_matches: list[SemanticMatch]
    action_matches: list[SemanticMatch]
    summary_supported: bool
    summary_complete: bool
    notes: str = Field(min_length=1, pattern=r"\S")


def index_records(records: list[dict], key: str, allowed_ids: set[str]) -> dict:
    indexed = {}
    for record in records:
        case_id = record[key]
        if case_id not in allowed_ids or case_id in indexed:
            raise ValueError(f"Unknown or duplicate case ID: {case_id}")
        indexed[case_id] = record
    return indexed


def count_matches(expected: list, predicted: list, matches: list[dict], actions: bool) -> int:
    seen_expected = set()
    seen_predicted = set()
    correct = 0
    for match in matches:
        expected_index = match["expected_index"]
        predicted_index = match["predicted_index"]
        if (type(expected_index) is not int or type(predicted_index) is not int
                or not 0 <= expected_index < len(expected)
                or not 0 <= predicted_index < len(predicted)):
            raise ValueError("Match index is outside its list.")
        if expected_index in seen_expected or predicted_index in seen_predicted:
            raise ValueError("A reference or prediction cannot be matched twice.")
        if not isinstance(match.get("reason"), str) or not match["reason"].strip():
            raise ValueError("Every semantic match needs a reason.")
        seen_expected.add(expected_index)
        seen_predicted.add(predicted_index)
        if not actions or all(expected[expected_index][field] == predicted[predicted_index][field]
                              for field in ["owner", "due_date"]):
            correct += 1
    return correct


def validate_judgment(case: dict, analysis: dict, value: dict) -> dict:
    judgment = MeetingJudgment.model_validate(value).model_dump()
    for kind, match_key in [("decisions", "decision_matches"), ("actions", "action_matches")]:
        count_matches(case["expected"][kind], analysis[kind], judgment[match_key], actions=kind == "actions")
    return judgment


def metrics(correct: int, extra: int, missed: int) -> dict:
    return {
        "correct": correct, "extra": extra, "missed": missed,
        "precision": correct / (correct + extra) if correct + extra else None,
        "recall": correct / (correct + missed) if correct + missed else None,
        "f1": 2 * correct / (2 * correct + extra + missed) if 2 * correct + extra + missed else None,
    }


def evaluate_predictions(cases: list[dict], run: dict, judgments: list[dict]) -> tuple[list[dict], dict]:
    case_ids = {case["id"] for case in cases}
    if len(case_ids) != len(cases) or not cases:
        raise ValueError("Reference cases must have unique IDs and cannot be empty.")
    predictions = index_records(run["predictions"], "case_id", case_ids)
    judged = index_records(judgments, "case_id", case_ids)
    rows = []
    for case in cases:
        case_id = case["id"]
        prediction = predictions.get(case_id, {"status": "missing"})
        status = prediction["status"]
        if status not in {"ok", "missing", "api_error", "response_error", "invalid_output"}:
            raise ValueError(f"Unrecognized prediction status for {case_id}.")
        output = {"decisions": [], "actions": []}
        judgment = {}
        judge_status = "not_needed"
        notes = "No successful extraction; expected items counted as missed."
        if status == "ok":
            try:
                output = MeetingAnalysis.model_validate(prediction["analysis"]).model_dump()
            except ValueError:
                raise ValueError(f"Saved successful prediction has invalid schema: {case_id}") from None
            record = judged.get(case_id, {})
            judge_status = "judge_error"
            notes = record.get("error", "Judgment missing.")
            if record.get("status") == "ok":
                try:
                    judgment = validate_judgment(case, output, record["judgment"])
                    judge_status = "ok"
                    notes = judgment["notes"]
                except (ValueError, KeyError):
                    notes = "Saved judgment is invalid."
        row = {
            "case_id": case_id, "extraction_status": status, "judge_status": judge_status,
            "schema_valid": status == "ok", "correct_items": None, "extra_items": None,
            "missed_items": None, "precision": None, "recall": None, "f1": None,
            "summary_supported": judgment.get("summary_supported"),
            "summary_complete": judgment.get("summary_complete"), "notes": notes,
        }
        for kind, match_key in [("decisions", "decision_matches"), ("actions", "action_matches")]:
            counts = {"correct": None, "extra": None, "missed": None}
            if judge_status != "judge_error":
                correct = count_matches(case["expected"][kind], output[kind],
                                        judgment.get(match_key, []), actions=kind == "actions")
                counts = {"correct": correct, "extra": len(output[kind]) - correct,
                          "missed": len(case["expected"][kind]) - correct}
            for name, count in counts.items():
                row[f"{kind}_{name}"] = count
        if judge_status != "judge_error":
            counts = {name: row[f"decisions_{name}"] + row[f"actions_{name}"]
                      for name in ["correct", "extra", "missed"]}
            scores = metrics(**counts)
            row.update({f"{name}_items": counts[name] for name in counts})
            row.update({name: scores[name] for name in ["precision", "recall", "f1"]})
        rows.append(row)

    judge_errors = sum(row["judge_status"] == "judge_error" for row in rows)
    successful = sum(row["schema_valid"] for row in rows)
    summary = {
        "case_count": len(cases), "successful_cases": successful,
        "extraction_failures": len(cases) - successful, "judge_errors": judge_errors,
        "evaluation_status": "incomplete" if judge_errors else "complete",
        "correct_items": None, "extra_items": None, "missed_items": None,
        "precision": None, "recall": None, "f1": None,
        "schema_compliance_of_successes": 1.0 if successful else None,
        "successful_attempt_rate": successful / len(cases),
        "summary_supported_count": sum(row["summary_supported"] is True for row in rows),
        "summary_complete_count": sum(row["summary_complete"] is True for row in rows),
        "summaries_needing_review": sum(
            row["judge_status"] == "ok" and
            (row["summary_supported"] is False or row["summary_complete"] is False)
            for row in rows
        ),
        "f1_target_met": None, "review_basis": "model_judged",
    }
    for kind in ["decisions", "actions"]:
        counts = {name: sum(row[f"{kind}_{name}"] for row in rows) if not judge_errors else None
                  for name in ["correct", "extra", "missed"]}
        summary.update({f"{kind}_{name}": count for name, count in counts.items()})
    if not judge_errors:
        counts = {name: sum(row[f"{name}_items"] for row in rows) for name in ["correct", "extra", "missed"]}
        scores = metrics(**counts)
        summary.update({f"{name}_items": counts[name] for name in counts})
        summary.update({name: scores[name] for name in ["precision", "recall", "f1"]})
        summary["f1_target_met"] = scores["f1"] is not None and scores["f1"] >= 0.85
    return rows, summary


def format_item(item) -> str:
    if isinstance(item, str):
        return item
    owner = item["owner"] if item["owner"] is not None else "not stated"
    due = item["due_date"] if item["due_date"] is not None else "not stated"
    return f"{item['action']} | owner: {owner} | due: {due}"


def compare_items(expected: list, predicted: list, matches: list[dict], actions: bool) -> list[dict]:
    if not expected and not predicted:
        return [{"golden": "(none)", "prediction": "(none)", "result": "Correctly empty",
                 "reason": "None expected or returned; this row adds no scored items."}]
    by_expected = {match["expected_index"]: match for match in matches}
    used_predictions = {match["predicted_index"] for match in matches}
    rows = []
    for index, item in enumerate(expected):
        match = by_expected.get(index)
        if match is None:
            rows.append({"golden": format_item(item), "prediction": "", "result": "Missed",
                         "reason": "No predicted item matched this reference."})
            continue
        actual = predicted[match["predicted_index"]]
        differences = []
        if actions:
            for field in ["owner", "due_date"]:
                if item[field] != actual[field]:
                    differences.append(f"{field.replace('_', ' ')} differs: golden={item[field] or 'not stated'}, prediction={actual[field] or 'not stated'}")
        rows.append({
            "golden": format_item(item), "prediction": format_item(actual),
            "result": "Incorrect" if differences else "Correct",
            "reason": "; ".join(differences) + ". Counts as one extra and one missed item."
                      if differences else match["reason"],
        })
    for index, item in enumerate(predicted):
        if index not in used_predictions:
            rows.append({"golden": "", "prediction": format_item(item), "result": "Extra",
                         "reason": "No reference item matched this prediction."})
    return rows


def comparison_rows(cases: list[dict], run: dict, judgments: list[dict], case_results: list[dict]) -> list[dict]:
    """Display already-validated judgments; never make new semantic decisions."""
    predictions = {record["case_id"]: record for record in run["predictions"]}
    judged = {record["case_id"]: record for record in judgments}
    statuses = {row["case_id"]: row for row in case_results}
    rows = []
    for case in cases:
        case_id = case["id"]
        status = statuses[case_id]
        expected = case["expected"]
        actual = predictions.get(case_id, {}).get("analysis") if status["schema_valid"] else None
        judgment = judged[case_id]["judgment"] if status["judge_status"] == "ok" else {}
        reason = status["notes"]
        result = "Extraction failed" if actual is None else "Not evaluated"
        if judgment:
            issues = []
            if not judgment["summary_supported"]:
                issues.append("Unsupported claim(s)")
            if not judgment["summary_complete"]:
                issues.append("Important detail missing")
            result = "Needs review" if issues else "Correct"
            reason = "; ".join(issues) + ". " + judgment["notes"] if issues else "Supported and includes the important reference meaning."
        rows.append({"case_id": case_id, "item": "Summary", "golden": expected["summary"],
                     "prediction": actual["summary"] if actual else "", "result": result, "reason": reason})
        for kind, label, match_key in [("decisions", "Decision", "decision_matches"),
                                       ("actions", "Action", "action_matches")]:
            predicted_items = actual[kind] if actual else []
            if status["judge_status"] == "judge_error":
                # No semantic alignment is known yet; do not invent item matches.
                comparisons = [{"golden": "\n".join(format_item(item) for item in expected[kind]) or "(none)",
                                "prediction": "\n".join(format_item(item) for item in predicted_items) or "(none)",
                                "result": "Not evaluated", "reason": status["notes"]}]
            else:
                comparisons = compare_items(expected[kind], predicted_items, judgment.get(match_key, []), actions=kind == "actions")
                if actual is None:
                    for row in comparisons:
                        row["reason"] = status["notes"]
                        if row["result"] == "Correctly empty":
                            row["result"] = "Extraction failed"
                            row["prediction"] = ""
            rows.extend({"case_id": case_id, "item": label, **row} for row in comparisons)
    return rows


def format_f1(value: float | None) -> str | None:
    return f"{value:.2%}" if value is not None else None


def summary_row(summary: dict) -> dict:
    """Keep the reader-facing summary small; full scores/metadata stay in JSON."""
    return {
        "run": summary["run"], "meetings": summary["case_count"],
        "valid_outputs": summary["successful_cases"],
        "correct": summary["correct_items"], "extra": summary["extra_items"], "missed": summary["missed_items"],
        "f1": format_f1(summary["f1"]), "summaries_needing_review": summary["summaries_needing_review"],
        "extraction_failures": summary["extraction_failures"], "judge_errors": summary["judge_errors"],
        "status": summary["evaluation_status"],
    }
