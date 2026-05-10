"""
baseline_run.py

Run ATP on one lexicon and extract learned rule paths.
Baseline run used for all other analysis files.

Outputs:
- baseline_summary.json
- baseline_rules.csv
- optional tree PDF if --tree_out is provided

Example:
PYTHONPATH=src python analysis/baseline_run.py \
  --input data/english/growth/child-0/500.txt \
  --child_id 0 \
  --lexicon_size 500 \
  --use_ipa true \
  --tree_out temp/child0_500 \
  --open_pdf false
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from atp import ATP
from utils import load_pairs, load_word_to_ipa

from io_utils import write_csv, write_json


def str2bool(value: str) -> bool:
    """Parse command-line boolean values."""
    value = value.lower()

    if value in {"true", "t", "1", "yes", "y"}:
        return True
    if value in {"false", "f", "0", "no", "n"}:
        return False

    raise argparse.ArgumentTypeError("Expected true or false.")


def load_word_to_ipa_safe():
    """
    Load IPA mappings without modifying Belth's code.

    Belth's load_word_to_ipa() assumes execution from src/. This wrapper
    temporarily switches to src/ so the original relative path works.
    """
    old_cwd = os.getcwd()
    project_root = Path(__file__).resolve().parents[1]

    try:
        os.chdir(project_root / "src")
        return load_word_to_ipa()
    finally:
        os.chdir(old_cwd)


def load_training_pairs(input_path: str, sep: str, use_ipa: bool):
    """Load one ATP training file, optionally converting words to IPA."""
    preprocessing = None

    if use_ipa:
        word_to_ipa = load_word_to_ipa_safe()

        def preprocessing(token: str) -> str:
            if token not in word_to_ipa:
                raise KeyError(f"Missing IPA mapping for token: {token}")
            return word_to_ipa[token]

    return load_pairs(input_path, sep=sep, preprocessing=preprocessing)


def canonical_conditions(path: List[str]) -> str:
    """
    Convert an ordered ATP path into a stable conjunction.

    Conditions are sorted so rules can be compared as condition sets rather
    than as ordered split sequences.
    """
    return " & ".join(sorted(path)) if path else "TRUE"


def make_rule_signature(path: List[str], rule: str) -> str:
    """Create the canonical rule signature used for comparison."""
    return f"{canonical_conditions(path)} => {rule}"


def is_productive_rule(node: Any) -> bool:
    """Return whether a terminal ATP node is productive."""
    try:
        return bool(node.switch_statement.productive)
    except Exception:
        return "No Productive Process" not in node.name


def extract_rule(node_name: str) -> str:
    """Extract the final rule text from an ATP terminal node name."""
    if "=>" in node_name:
        return node_name.split("=>", 1)[1].strip()
    return node_name.strip()


def traverse_tree(node: Any, path: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Traverse the learned ATP tree and return one record per terminal rule.
    """
    if path is None:
        path = []

    if node.num_children() == 0:
        rule = extract_rule(node.name)

        return [
            {
                "path": path,
                "conditions": canonical_conditions(path),
                "rule": rule,
                "productive": is_productive_rule(node),
                "rule_signature": make_rule_signature(path, rule),
                "depth": len(path),
                "terminal_name": node.name,
            }
        ]

    records: List[Dict[str, Any]] = []

    for condition_tuple, child in node.get_children():
        positive, feature = condition_tuple
        condition = str(feature) if positive else f"¬{feature}"
        records.extend(traverse_tree(child, path + [condition]))

    return records


def run_one_file(
    input_path: str,
    sep: str = " ",
    use_ipa: bool = True,
    tree_out: Optional[str] = None,
    open_pdf: bool = False,
    child_id: Optional[int] = None,
    lexicon_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Train ATP on one lexicon and return a structured summary."""
    pairs, feature_space = load_training_pairs(input_path, sep, use_ipa)

    model = ATP(
        apply_phonology=use_ipa,
        feature_space=feature_space,
    ).train(pairs)

    rules = traverse_tree(model.root)
    productive_rules = [rule for rule in rules if rule["productive"]]

    tree_pdf = None
    if tree_out:
        Path(tree_out).parent.mkdir(parents=True, exist_ok=True)
        model.plot_tree(tree_out, open_pdf=open_pdf)
        tree_pdf = f"{tree_out}.pdf"

    return {
        "child_id": child_id,
        "lexicon_size": lexicon_size,
        "input_path": input_path,
        "num_pairs": len(pairs),
        "feature_space": sorted(feature_space),
        "num_rules": len(rules),
        "num_productive_rules": len(productive_rules),
        "num_nonproductive_rules": len(rules) - len(productive_rules),
        "tree_depth": max((rule["depth"] for rule in rules), default=0),
        "rules": rules,
        "tree_pdf": tree_pdf,
    }


def summary_for_output(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return compact run-level summary for JSON/CSV outputs."""
    return {
        "child_id": summary["child_id"],
        "lexicon_size": summary["lexicon_size"],
        "input_path": summary["input_path"],
        "num_pairs": summary["num_pairs"],
        "feature_space": summary["feature_space"],
        "num_rules": summary["num_rules"],
        "num_productive_rules": summary["num_productive_rules"],
        "num_nonproductive_rules": summary["num_nonproductive_rules"],
        "tree_depth": summary["tree_depth"],
        "tree_pdf": summary["tree_pdf"],
    }


def rule_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten rule records for CSV output."""
    rows = []

    for rule_index, rule in enumerate(summary["rules"]):
        rows.append(
            {
                "child_id": summary["child_id"],
                "lexicon_size": summary["lexicon_size"],
                "input_path": summary["input_path"],
                "rule_index": rule_index,
                "rule_signature": rule["rule_signature"],
                "conditions": rule["conditions"],
                "rule": rule["rule"],
                "productive": rule["productive"],
                "depth": rule["depth"],
                "path_ordered": " > ".join(rule["path"]),
                "terminal_name": rule["terminal_name"],
            }
        )

    return rows


SUMMARY_FIELDS = [
    "child_id",
    "lexicon_size",
    "input_path",
    "num_pairs",
    "feature_space",
    "num_rules",
    "num_productive_rules",
    "num_nonproductive_rules",
    "tree_depth",
    "tree_pdf",
]

RULE_FIELDS = [
    "child_id",
    "lexicon_size",
    "input_path",
    "rule_index",
    "rule_signature",
    "conditions",
    "rule",
    "productive",
    "depth",
    "path_ordered",
    "terminal_name",
]


def write_outputs(summary: Dict[str, Any], summary_json: str, rules_csv: str) -> None:
    """Write compact summary JSON and all rules CSV."""
    write_json(summary_json, summary_for_output(summary))
    write_csv(rules_csv, rule_rows(summary), RULE_FIELDS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run ATP on one lexicon and extract learned rule paths."
    )

    parser.add_argument("--input", required=True)
    parser.add_argument("--sep", default=" ")
    parser.add_argument("--use_ipa", type=str2bool, default=True)
    parser.add_argument("--child_id", type=int, default=None)
    parser.add_argument("--lexicon_size", type=int, default=None)
    parser.add_argument("--tree_out", default=None, help="Tree PDF path prefix; omit .pdf.")
    parser.add_argument("--open_pdf", type=str2bool, default=False)
    parser.add_argument("--summary_json", default="temp/baseline_summary.json")
    parser.add_argument("--rules_csv", default="temp/baseline_rules.csv")

    args = parser.parse_args()

    summary = run_one_file(
        input_path=args.input,
        sep=args.sep,
        use_ipa=args.use_ipa,
        tree_out=args.tree_out,
        open_pdf=args.open_pdf,
        child_id=args.child_id,
        lexicon_size=args.lexicon_size,
    )

    write_outputs(summary, args.summary_json, args.rules_csv)

    print("Finished baseline run.")
    print(f"Input: {summary['input_path']}")
    print(f"Pairs: {summary['num_pairs']}")
    print(f"Rules: {summary['num_rules']}")
    print(f"Productive rules: {summary['num_productive_rules']}")
    print(f"Nonproductive rules: {summary['num_nonproductive_rules']}")
    print(f"Tree depth: {summary['tree_depth']}")

    if summary["tree_pdf"]:
        print(f"Tree PDF: {summary['tree_pdf']}")


if __name__ == "__main__":
    main()