"""
baseline_run.py

Run Belth et al.'s ATP model on ONE lexicon file.

This file is the core baseline. It answers:
    "Can ATP be trained on one child-sized lexicon, and what rule paths does it learn?"

Other scripts import run_one_file() from here.

A learned ATP rule is represented as:

    full path conditions + final leaf rule

For comparison, this project treats path conditions as a conjunction/set.
That means the canonical comparison unit is:
    sorted conditions => final rule

Example:
    ¬PRS & PST & k# => inflected = lemma + t

Example run:
from src
python baseline_run.py \
  --input ../data/english/growth/child-0/500.txt \
  --child_id 0 \
  --lexicon_size 500 \
  --sep " " \
  --use_ipa true \
  --tree_out ../temp/child0_500
"""

from __future__ import annotations

import argparse
import csv
import json
from typing import Any, Dict, List, Optional

from atp import ATP
from utils import load_pairs, load_word_to_ipa


def str2bool(value: str) -> bool:
    """Parse command-line true/false strings."""
    value = value.lower()
    if value in {"true", "t", "1", "yes", "y"}:
        return True
    if value in {"false", "f", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected true or false.")


def is_leaf_productive(leaf) -> bool:
    """
    Return whether an ATP leaf corresponds to a productive process.

    ATP stores this in leaf.switch_statement.productive.
    The fallback checks the printed leaf name.
    """
    try:
        return bool(leaf.switch_statement.productive)
    except Exception:
        return "No Productive Process" not in leaf.name


def extract_leaf_rule(leaf_name: str) -> str:
    """
    Extract the rule part from a printed ATP leaf name.

    Example:
        '¬PRS,PST,k# => inflected = lemma + t'
    becomes:
        'inflected = lemma + t'
    """
    if "=>" in leaf_name:
        return leaf_name.split("=>", 1)[1].strip()
    return leaf_name.strip()


def compute_tree_depth(node) -> int:
    """
    Compute maximum tree depth.

    A leaf has depth 0. A tree with one split below root has depth 1.
    """
    if node.num_children() == 0:
        return 0
    return 1 + max(compute_tree_depth(child) for _, child in node.get_children())


def canonical_conditions(path: List[str]) -> str:
    """
    Convert ordered path conditions into a stable conjunction string.

    The order of ATP splits is not used as the comparison criterion here.
    Instead, the conditions are sorted and treated as a set/conjunction.
    """
    if not path:
        return "TRUE"
    return " & ".join(sorted(path))


def make_rule_signature(path: List[str], rule: str) -> str:
    """
    Create the exact rule signature used for comparison.

    Two productive rules are considered the same only if both their condition
    set and final rule string match.
    """
    return f"{canonical_conditions(path)} => {rule}"


def traverse_tree_paths(node, path_prefix: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Traverse an ATP tree and return one record per leaf.

    Each leaf record includes:
        - ordered path
        - canonical condition set
        - final rule
        - productivity status
        - canonical rule signature
        - original ATP leaf name
    """
    if path_prefix is None:
        path_prefix = []

    if node.num_children() == 0:
        rule = extract_leaf_rule(node.name)
        productive = is_leaf_productive(node)

        return [
            {
                "path": path_prefix,
                "conditions": canonical_conditions(path_prefix),
                "rule": rule,
                "productive": productive,
                "rule_signature": make_rule_signature(path_prefix, rule),
                "leaf_name": node.name,
                "depth": len(path_prefix),
            }
        ]

    results: List[Dict[str, Any]] = []

    for branch_condition, child in node.get_children():
        positive, split_feature = branch_condition
        condition = str(split_feature) if positive else f"¬{split_feature}"
        results.extend(traverse_tree_paths(child, path_prefix + [condition]))

    return results


def load_training_pairs(input_path: str, sep: str, use_ipa: bool):
    """
    Load one ATP training file.

    For the English growth data, use_ipa=True is usually appropriate because
    Belth's English analyses are phonology-aware.
    """
    preprocessing = None

    if use_ipa:
        word_to_ipa = load_word_to_ipa()
        preprocessing = lambda s: word_to_ipa[s]

    return load_pairs(input_path, sep=sep, preprocessing=preprocessing)


def run_one_file(
    input_path: str,
    sep: str = " ",
    use_ipa: bool = True,
    tree_out: Optional[str] = None,
    open_pdf: bool = False,
    child_id: Optional[int] = None,
    lexicon_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Train ATP on one lexicon and return a structured summary.

    This function is imported by the other scripts. It should remain the single
    source of truth for one-file ATP runs.
    """
    pairs, feature_space = load_training_pairs(input_path, sep=sep, use_ipa=use_ipa)

    atp_model = ATP(
        apply_phonology=use_ipa,
        feature_space=feature_space,
    ).train(pairs)

    leaf_paths = traverse_tree_paths(atp_model.root)
    productive_rules = [leaf for leaf in leaf_paths if leaf["productive"]]

    summary = {
        "child_id": child_id,
        "lexicon_size": lexicon_size,
        "input_path": input_path,
        "num_pairs": len(pairs),
        "feature_space": sorted(feature_space),
        "num_leaves": len(leaf_paths),
        "num_productive_leaves": len(productive_rules),
        "num_nonproductive_leaves": len(leaf_paths) - len(productive_rules),
        "tree_depth": compute_tree_depth(atp_model.root),
        "leaf_paths": leaf_paths,
        "productive_rules": productive_rules,
        "tree_pdf": None,
    }

    if tree_out is not None:
        atp_model.plot_tree(tree_out, open_pdf=open_pdf)
        summary["tree_pdf"] = f"{tree_out}.pdf"

    return summary


def write_one_run_outputs(
    summary: Dict[str, Any],
    summary_json: str,
    leaf_csv: str,
    productive_csv: str,
) -> None:
    """
    Optional debug output for one baseline run.

    The larger experiments write their own CSV files, but this is useful when
    testing a single lexicon.
    """
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    fields = [
        "child_id",
        "lexicon_size",
        "input_path",
        "num_leaves",
        "num_productive_leaves",
        "num_nonproductive_leaves",
        "tree_depth",
        "leaf_index",
        "productive",
        "depth",
        "conditions",
        "rule",
        "rule_signature",
        "path_ordered",
        "leaf_name",
    ]

    def make_row(i: int, leaf: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "child_id": summary["child_id"],
            "lexicon_size": summary["lexicon_size"],
            "input_path": summary["input_path"],
            "num_leaves": summary["num_leaves"],
            "num_productive_leaves": summary["num_productive_leaves"],
            "num_nonproductive_leaves": summary["num_nonproductive_leaves"],
            "tree_depth": summary["tree_depth"],
            "leaf_index": i,
            "productive": leaf["productive"],
            "depth": leaf["depth"],
            "conditions": leaf["conditions"],
            "rule": leaf["rule"],
            "rule_signature": leaf["rule_signature"],
            "path_ordered": " > ".join(leaf["path"]),
            "leaf_name": leaf["leaf_name"],
        }

    with open(leaf_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, leaf in enumerate(summary["leaf_paths"]):
            writer.writerow(make_row(i, leaf))

    with open(productive_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, leaf in enumerate(summary["productive_rules"]):
            writer.writerow(make_row(i, leaf))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ATP on one lexicon.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--sep", default=" ")
    parser.add_argument("--use_ipa", type=str2bool, default=True)
    parser.add_argument("--child_id", type=int, default=None)
    parser.add_argument("--lexicon_size", type=int, default=None)
    parser.add_argument("--tree_out", default=None)
    parser.add_argument("--open_pdf", type=str2bool, default=False)
    parser.add_argument("--summary_json", default="../temp/baseline_summary.json")
    parser.add_argument("--leaf_csv", default="../temp/baseline_leaf_paths.csv")
    parser.add_argument("--productive_csv", default="../temp/baseline_productive_rules.csv")

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

    write_one_run_outputs(
        summary=summary,
        summary_json=args.summary_json,
        leaf_csv=args.leaf_csv,
        productive_csv=args.productive_csv,
    )

    print("Finished one-file ATP baseline.")
    print(f"Input: {summary['input_path']}")
    print(f"Leaves: {summary['num_leaves']}")
    print(f"Productive leaves: {summary['num_productive_leaves']}")
    print(f"Nonproductive leaves: {summary['num_nonproductive_leaves']}")
    print(f"Tree depth: {summary['tree_depth']}")


if __name__ == "__main__":
    main()