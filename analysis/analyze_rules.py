"""
analyze_rules.py

Analyze ATP rule-path stability and recurrence.

Inputs:
- batch_summary.csv
- batch_rules.csv

Outputs:
- complexity_by_size.csv
- within_child_rule_overlap.csv
- cross_child_rule_recurrence.csv
- rule_path_analysis_summary.txt

Example:
PYTHONPATH=src python analysis/analyze_rules.py \
  --summary_csv temp/batch_rule_paths_100children/batch_summary.csv \
  --rules_csv temp/batch_rule_paths_100children/batch_rules.csv \
  --out_dir temp/rule_analysis_100children \
  --interesting_threshold 0.3
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from io_utils import write_csv


def read_csv(path: str) -> List[Dict[str, str]]:
    """Read a CSV into a list of dictionaries."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def is_true(value: str) -> bool:
    """Parse boolean values read from CSV."""
    return str(value).lower() in {"true", "1", "yes", "y"}


def productive_only(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Keep only productive rule rows."""
    return [row for row in rows if is_true(row["productive"])]


def rule_sets_by_child_and_size(rows: List[Dict[str, str]]) -> Dict[Tuple[str, int], Set[str]]:
    """Return (child_id, lexicon_size) -> set(rule_signature)."""
    result: Dict[Tuple[str, int], Set[str]] = defaultdict(set)

    for row in rows:
        child_id = row["child_id"]
        lexicon_size = int(row["lexicon_size"])
        result[(child_id, lexicon_size)].add(row["rule_signature"])

    return result


def within_child_overlap(rows: List[Dict[str, str]]) -> List[Dict]:
    """Compare exact productive rule sets across adjacent lexicon sizes."""
    rule_sets = rule_sets_by_child_and_size(rows)

    sizes_by_child: Dict[str, List[int]] = defaultdict(list)
    for child_id, lexicon_size in rule_sets.keys():
        sizes_by_child[child_id].append(lexicon_size)

    output = []

    for child_id in sorted(sizes_by_child.keys(), key=lambda x: int(x)):
        sizes = sorted(set(sizes_by_child[child_id]))

        for size_a, size_b in zip(sizes, sizes[1:]):
            rules_a = rule_sets[(child_id, size_a)]
            rules_b = rule_sets[(child_id, size_b)]

            shared = rules_a & rules_b
            gained = rules_b - rules_a
            lost = rules_a - rules_b
            union = rules_a | rules_b

            output.append(
                {
                    "child_id": child_id,
                    "size_a": size_a,
                    "size_b": size_b,
                    "num_rules_a": len(rules_a),
                    "num_rules_b": len(rules_b),
                    "num_shared_rules": len(shared),
                    "jaccard_overlap": len(shared) / len(union) if union else 0.0,
                    "shared_rules": " || ".join(sorted(shared)),
                    "rules_gained": " || ".join(sorted(gained)),
                    "rules_lost": " || ".join(sorted(lost)),
                }
            )

    return output


def cross_child_recurrence(rows: List[Dict[str, str]]) -> List[Dict]:
    """Count exact productive rule recurrence across children at each size."""
    children_by_size: Dict[int, Set[str]] = defaultdict(set)
    children_by_size_rule: Dict[Tuple[int, str], Set[str]] = defaultdict(set)

    for row in rows:
        lexicon_size = int(row["lexicon_size"])
        child_id = row["child_id"]
        signature = row["rule_signature"]

        children_by_size[lexicon_size].add(child_id)
        children_by_size_rule[(lexicon_size, signature)].add(child_id)

    output = []

    for (lexicon_size, signature), children in children_by_size_rule.items():
        total_children = len(children_by_size[lexicon_size])

        output.append(
            {
                "lexicon_size": lexicon_size,
                "rule_signature": signature,
                "num_children_with_rule": len(children),
                "num_children_at_size": total_children,
                "proportion_children_with_rule": (
                    len(children) / total_children if total_children else 0.0
                ),
                "children": ", ".join(sorted(children, key=lambda x: int(x))),
            }
        )

    output.sort(
        key=lambda row: (
            int(row["lexicon_size"]),
            -int(row["num_children_with_rule"]),
            row["rule_signature"],
        )
    )

    return output


def summarize_tree_complexity(summary_rows: List[Dict[str, str]]) -> List[Dict]:
    """Summarize tree complexity by lexicon size."""
    grouped: Dict[int, List[Dict[str, str]]] = defaultdict(list)

    for row in summary_rows:
        grouped[int(row["lexicon_size"])].append(row)

    output = []

    for lexicon_size, group in sorted(grouped.items()):
        depths = [int(row["tree_depth"]) for row in group]
        rules = [int(row["num_rules"]) for row in group]
        productive = [int(row["num_productive_rules"]) for row in group]
        nonproductive = [int(row["num_nonproductive_rules"]) for row in group]

        output.append(
            {
                "lexicon_size": lexicon_size,
                "num_runs": len(group),
                "mean_tree_depth": sum(depths) / len(depths),
                "min_tree_depth": min(depths),
                "max_tree_depth": max(depths),
                "mean_num_rules": sum(rules) / len(rules),
                "mean_productive_rules": sum(productive) / len(productive),
                "mean_nonproductive_rules": sum(nonproductive) / len(nonproductive),
                "num_fully_productive_trees": sum(1 for value in nonproductive if value == 0),
            }
        )

    return output


def write_summary_text(
    out_path: str,
    complexity_rows: List[Dict],
    within_rows: List[Dict],
    cross_rows: List[Dict],
    interesting_threshold: float,
) -> None:
    """Write a short plain-English analysis summary."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("ATP Rule Path Analysis Summary\n")
        f.write("=" * 80 + "\n\n")

        f.write("Tree complexity by lexicon size\n")
        f.write("-" * 80 + "\n")
        for row in complexity_rows:
            f.write(
                f"Size {row['lexicon_size']}: "
                f"mean depth={row['mean_tree_depth']:.2f}, "
                f"depth range={row['min_tree_depth']}-{row['max_tree_depth']}, "
                f"mean rules={row['mean_num_rules']:.2f}, "
                f"mean productive rules={row['mean_productive_rules']:.2f}, "
                f"mean nonproductive rules={row['mean_nonproductive_rules']:.2f}, "
                f"fully productive trees={row['num_fully_productive_trees']}/"
                f"{row['num_runs']}\n"
            )

        f.write("\nWithin-child adjacent-stage stability\n")
        f.write("-" * 80 + "\n")
        if within_rows:
            avg_jaccard = sum(float(row["jaccard_overlap"]) for row in within_rows) / len(within_rows)
            f.write(f"Mean adjacent-stage Jaccard overlap: {avg_jaccard:.2f}\n")
        else:
            f.write("No within-child comparisons available.\n")

        f.write("\nCross-child recurrent productive rules\n")
        f.write("-" * 80 + "\n")
        interesting = [
            row for row in cross_rows
            if float(row["proportion_children_with_rule"]) >= interesting_threshold
        ]

        if not interesting:
            f.write(
                f"No productive rule reached the recurrence threshold of "
                f"{interesting_threshold:.2f}.\n"
            )
        else:
            for row in interesting:
                f.write(
                    f"Size {row['lexicon_size']}: "
                    f"{row['rule_signature']} appeared in "
                    f"{row['num_children_with_rule']}/"
                    f"{row['num_children_at_size']} children "
                    f"({float(row['proportion_children_with_rule']):.2f}).\n"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze ATP learned rule paths.")
    parser.add_argument("--summary_csv", required=True)
    parser.add_argument("--rules_csv", required=True)
    parser.add_argument("--out_dir", default="temp/rule_analysis")
    parser.add_argument(
        "--interesting_threshold",
        type=float,
        default=0.6,
        help="Minimum cross-child proportion for a rule to be highlighted.",
    )

    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    summary_rows = read_csv(args.summary_csv)
    all_rule_rows = read_csv(args.rules_csv)
    productive_rows = productive_only(all_rule_rows)

    complexity_rows = summarize_tree_complexity(summary_rows)
    within_rows = within_child_overlap(productive_rows)
    cross_rows = cross_child_recurrence(productive_rows)

    write_csv(
        os.path.join(args.out_dir, "complexity_by_size.csv"),
        complexity_rows,
        [
            "lexicon_size",
            "num_runs",
            "mean_tree_depth",
            "min_tree_depth",
            "max_tree_depth",
            "mean_num_rules",
            "mean_productive_rules",
            "mean_nonproductive_rules",
            "num_fully_productive_trees",
        ],
    )

    write_csv(
        os.path.join(args.out_dir, "within_child_rule_overlap.csv"),
        within_rows,
        [
            "child_id",
            "size_a",
            "size_b",
            "num_rules_a",
            "num_rules_b",
            "num_shared_rules",
            "jaccard_overlap",
            "shared_rules",
            "rules_gained",
            "rules_lost",
        ],
    )

    write_csv(
        os.path.join(args.out_dir, "cross_child_rule_recurrence.csv"),
        cross_rows,
        [
            "lexicon_size",
            "rule_signature",
            "num_children_with_rule",
            "num_children_at_size",
            "proportion_children_with_rule",
            "children",
        ],
    )

    write_summary_text(
        out_path=os.path.join(args.out_dir, "rule_path_analysis_summary.txt"),
        complexity_rows=complexity_rows,
        within_rows=within_rows,
        cross_rows=cross_rows,
        interesting_threshold=args.interesting_threshold,
    )

    print(f"Saved rule-path analysis to: {args.out_dir}")
    print("Most useful file first:")
    print(os.path.join(args.out_dir, "rule_path_analysis_summary.txt"))


if __name__ == "__main__":
    main()