"""Compile the authored case boards into the campaign's existing puzzle format."""

def apply_caseboards(content, *collections):
    tasks = {task["id"]: task for scene in content["scenes"] for task in scene["tasks"]}
    for cases in collections:
        for task_id, case in cases.items():
            task = tasks[task_id]
            if "puzzle" in task or task_id == "p_bay.tune":
                raise ValueError(f"{task_id} already has an instrument")
            if not (case["intro"] and case["evidence"] and len(case["hints"]) == 3 and 2 <= len(case["stages"]) <= 3):
                raise ValueError(f"Incomplete case board for {task_id}")
            rows, solution = [], []
            for stage in case["stages"]:
                pieces, slots, answer = stage["pieces"], stage["slots"], stage["answer"]
                if (stage["mode"] not in ("order", "match", "route") or not stage["prompt"]
                        or len(slots) != len(pieces) or not 3 <= len(slots) <= 5
                        or len(set(pieces)) != len(pieces) or sorted(answer) != list(range(len(slots)))):
                    raise ValueError(f"Invalid {stage['mode']} layout for {task_id}")
                rows.extend({"label": slot, "options": pieces} for slot in slots)
                solution.extend(answer)
            task["puzzle"] = {
                "presentation": "case_board", "instruction": case["intro"],
                "evidence": case["evidence"], "stages": case["stages"], "solution": solution,
                "rows": rows, "hints": case["hints"]
            }
            task["hints"] = case["hints"]
