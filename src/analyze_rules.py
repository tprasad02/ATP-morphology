"""
analyze_rules.py

Analyze exact productive ATP rule paths.

A productive ATP rule is compared using:
    sorted path conditions + final productive leaf rule

Example:
    ¬PRS & PST & k# => inflected = lemma + t


Each simulated child is trained on a different sampled lexicon. Therefore,
counting how often ATP checks a local split such as PST or PL can be misleading.
A local branch may occur more often simply because a lexicon contains different
kinds of words.

This file instead asks:
    1. Within a child, do productive rule signatures persist across stages?
    2. Across children, do exact productive rule signatures recur at a stage?
    3. How complex are the learned trees at each lexicon size?

Example run:
from src    
python analyze_rules.py \
  --summary_csv ../temp/batch_rule_paths/batch_summary.csv \
  --productive_csv ../temp/batch_rule_paths/batch_productive_rules.csv \
  --out_dir ../temp/rule_analysis \
  --interesting_threshold 0.6
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def read_csv(path: str) -> List[Dict[str, str]]:
    """Read a CSV into a list of dictionaries."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]) -> None:
    """Write dictionaries to a CSV file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rule_sets_by_child_and_size(rows: List[Dict[str, str]]) -> Dict[Tuple[str, int], Set[str]]:
    """
    Build:
        (child_id, lexicon_size) -> set(rule_signature)

    This gives one productive rule set per ATP run.
    """
    result: Dict[Tuple[str, int], Set[str]] = defaultdict(set)

    for row in rows:
        child_id = row["child_id"]
        size = int(row["lexicon_size"])
        signature = row["rule_signature"]
        result[(child_id, size)].add(signature)

    return result


def within_child_overlap(rows: List[Dict[str, str]]) -> List[Dict]:
    """
    Compare adjacent growth stages within each child.

    This asks:
        When a child's lexicon grows, which exact productive rules persist,
        which disappear, and which are newly gained?
    """
    rule_sets = rule_sets_by_child_and_size(rows)

    sizes_by_child: Dict[str, List[int]] = defaultdict(list)
    for child, size in rule_sets.keys():
        sizes_by_child[child].append(size)

    output = []

    for child in sorted(sizes_by_child.keys(), key=lambda x: int(x)):
        sizes = sorted(set(sizes_by_child[child]))

        for size_a, size_b in zip(sizes, sizes[1:]):
            rules_a = rule_sets[(child, size_a)]
            rules_b = rule_sets[(child, size_b)]

            shared = rules_a & rules_b
            gained = rules_b - rules_a
            lost = rules_a - rules_b
            union = rules_a | rules_b

            output.append(
                {
                    "child_id": child,
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
    """
    Count exact productive rule recurrence across children at each lexicon size.

    This asks:
        At size 500, for example, how many children produced the exact same
        productive rule signature?
    """
    children_by_size: Dict[int, Set[str]] = defaultdict(set)
    children_by_size_rule: Dict[Tuple[int, str], Set[str]] = defaultdict(set)

    for row in rows:
        size = int(row["lexicon_size"])
        child = row["child_id"]
        signature = row["rule_signature"]

        children_by_size[size].add(child)
        children_by_size_rule[(size, signature)].add(child)

    output = []

    for (size, signature), children in children_by_size_rule.items():
        total_children = len(children_by_size[size])

        output.append(
            {
                "lexicon_size": size,
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
        key=lambda r: (
            int(r["lexicon_size"]),
            -int(r["num_children_with_rule"]),
            r["rule_signature"],
        )
    )

    return output


def summarize_tree_complexity(summary_rows: List[Dict[str, str]]) -> List[Dict]:
    """
    Summarize tree size/complexity by lexicon size.

    This is descriptive only. It does not claim acquisition directly.
    It tells us whether ATP trees tend to get deeper, shallower, more productive,
    or less exception-heavy at different lexicon sizes.
    """
    grouped: Dict[int, List[Dict[str, str]]] = defaultdict(list)

    for row in summary_rows:
        grouped[int(row["lexicon_size"])].append(row)

    output = []

    for size, group in sorted(grouped.items()):
        depths = [int(r["tree_depth"]) for r in group]
        leaves = [int(r["num_leaves"]) for r in group]
        prod = [int(r["num_productive_leaves"]) for r in group]
        nonprod = [int(r["num_nonproductive_leaves"]) for r in group]

        output.append(
            {
                "lexicon_size": size,
                "num_runs": len(group),
                "mean_tree_depth": sum(depths) / len(depths),
                "min_tree_depth": min(depths),
                "max_tree_depth": max(depths),
                "mean_num_leaves": sum(leaves) / len(leaves),
                "mean_productive_leaves": sum(prod) / len(prod),
                "mean_nonproductive_leaves": sum(nonprod) / len(nonprod),
                "num_fully_productive_trees": sum(1 for x in nonprod if x == 0),
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
    """
    Write a plain-English summary of the analysis.
    """
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("ATP Rule Path Analysis Summary\n")
        f.write("=" * 80 + "\n\n")

        f.write("Methodological note\n")
        f.write("-" * 80 + "\n")
        f.write(
            "This analysis does not build an aggregate tree or count local split "
            "frequencies. Because each simulated child has a different sampled "
            "lexicon, local branch counts are not directly comparable. Instead, "
            "the analysis compares exact productive ATP rule signatures: sorted "
            "path conditions plus the final leaf rule.\n\n"
        )

        f.write("Tree complexity by lexicon size\n")
        f.write("-" * 80 + "\n")
        for row in complexity_rows:
            f.write(
                f"Size {row['lexicon_size']}: "
                f"mean depth={row['mean_tree_depth']:.2f}, "
                f"depth range={row['min_tree_depth']}-{row['max_tree_depth']}, "
                f"mean leaves={row['mean_num_leaves']:.2f}, "
                f"mean productive leaves={row['mean_productive_leaves']:.2f}, "
                f"mean nonproductive leaves={row['mean_nonproductive_leaves']:.2f}, "
                f"fully productive trees={row['num_fully_productive_trees']}/"
                f"{row['num_runs']}\n"
            )

        f.write("\nWithin-child adjacent-stage stability\n")
        f.write("-" * 80 + "\n")
        if within_rows:
            avg_jaccard = sum(float(r["jaccard_overlap"]) for r in within_rows) / len(within_rows)
            f.write(f"Mean adjacent-stage Jaccard overlap: {avg_jaccard:.2f}\n")
            f.write(
                "This measures how much the exact productive rule set persists "
                "from one growth stage to the next.\n"
            )
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
                f"{interesting_threshold:.2f} across children.\n"
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

        f.write("\nInterpretive caution\n")
        f.write("-" * 80 + "\n")
        f.write(
            "A productive rule at an earlier lexicon size should not automatically "
            "be interpreted as correct acquisition. It may be temporarily supported "
            "by a particular sampled lexicon and later disappear or be refined. "
            "For that reason, recurring or persistent exact rule signatures are "
            "more informative than isolated productive leaves.\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze exact ATP productive rule paths.")
    parser.add_argument("--summary_csv", required=True)
    parser.add_argument("--productive_csv", required=True)
    parser.add_argument("--out_dir", default="../temp/rule_analysis")
    parser.add_argument(
        "--interesting_threshold",
        type=float,
        default=0.6,
        help="Minimum cross-child proportion for a rule to be highlighted.",
    )

    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    summary_rows = read_csv(args.summary_csv)
    productive_rows = read_csv(args.productive_csv)

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
            "mean_num_leaves",
            "mean_productive_leaves",
            "mean_nonproductive_leaves",
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