"""
analyze_splits.py

Read ATP batch summaries and compute aggregate analyses.

Input:
A JSONL file produced by:
    - single_child_growth.py
    - batch_run_atp.py
Each line is one structured ATP run summary.

Output:
This script writes several CSVs:
    1. stage_first_split_counts.csv
    2. stage_first_split_most_common.csv
    3. tree_depth_distribution.csv
    4. productive_leaf_summary.csv
    5. weighted_split_edges.csv
    6. weighted_leaf_edges.csv

These outputs let us answer:
    - What is the most common first split at each growth stage?
    - How does tree depth vary across children/stages?
    - How many productive leaves do trees tend to have?
    - What split transitions recur across ATP trees?

We do NOT want to force all ATP trees into one identical literal tree.
This is because different child/stage inputs can produce different trees.
Therefore, this script instead constructs a weighted meta-graph:
parent split -> child split
with edge weights = number of runs showing that transition.

This is a much better aggregate representation of tree behavior.

From src/:

    python analyze_splits.py \
        --input_jsonl ../temp/batch_runs.jsonl \
        --out_dir ../temp/analysis
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

import pandas as pd


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    Load a JSONL file into a list of dictionaries.
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def most_common_first_split_by_stage(
    rows: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute:
        1. counts of first splits by growth stage
        2. most common first split by growth stage

    Returns:
    counts_df:
        one row per (growth_size, first_split)
    most_common_df:
        one row per growth_size
    """
    count_rows = []
    most_common_rows = []

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["growth_size"]].append(row["first_split"])

    for growth_size in sorted(grouped.keys()):
        counts = Counter(grouped[growth_size])

        for split, count in counts.items():
            count_rows.append(
                {
                    "growth_size": growth_size,
                    "first_split": split,
                    "count": count,
                }
            )

        split, count = counts.most_common(1)[0]
        most_common_rows.append(
            {
                "growth_size": growth_size,
                "most_common_first_split": split,
                "count": count,
                "num_runs": len(grouped[growth_size]),
                "proportion": count / len(grouped[growth_size]),
            }
        )

    return pd.DataFrame(count_rows), pd.DataFrame(most_common_rows)


def tree_depth_distribution(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Build a dataframe of tree depths by child and growth stage.
    """
    out = []
    for row in rows:
        out.append(
            {
                "child_id": row.get("child_id"),
                "growth_size": row.get("growth_size"),
                "tree_depth": row.get("tree_depth"),
                "num_leaves": row.get("num_leaves"),
            }
        )
    return pd.DataFrame(out)


def productive_leaf_summary(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Summarize productive and nonproductive leaf counts per run.
    """
    out = []
    for row in rows:
        out.append(
            {
                "child_id": row.get("child_id"),
                "growth_size": row.get("growth_size"),
                "num_pairs": row.get("num_pairs"),
                "num_leaves": row.get("num_leaves"),
                "num_productive_leaves": row.get("num_productive_leaves"),
                "num_nonproductive_leaves": row.get("num_nonproductive_leaves"),
            }
        )
    return pd.DataFrame(out)


def build_weighted_split_edges(
    rows: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build weighted meta-graph edges from ATP leaf paths.

    Create two edge tables:

    1. weighted_split_edges:
       transitions among split labels
       Example:
           ROOT -> PRS
           PRS -> ¬PL

    2. weighted_leaf_edges:
       transitions from final split label -> leaf rule
       Example:
           ¬PRS -> inflected = lemma + s

    Returns:
    split_edges_df, leaf_edges_df
    """
    split_edge_counts = Counter()
    leaf_edge_counts = Counter()

    for row in rows:
        for leaf in row["leaf_paths"]:
            path = leaf["path"]
            rule = leaf["rule"]

            # If there is no path, attach the rule directly to ROOT
            if len(path) == 0:
                leaf_edge_counts[("ROOT", rule)] += 1
                continue

            # ROOT -> first split
            split_edge_counts[("ROOT", path[0])] += 1

            # split -> split transitions
            for i in range(len(path) - 1):
                split_edge_counts[(path[i], path[i + 1])] += 1

            # final split -> leaf rule
            leaf_edge_counts[(path[-1], rule)] += 1

    split_rows = []
    for (source, target), weight in split_edge_counts.items():
        split_rows.append(
            {
                "source": source,
                "target": target,
                "weight": weight,
                "edge_type": "split_transition",
            }
        )

    leaf_rows = []
    for (source, target), weight in leaf_edge_counts.items():
        leaf_rows.append(
            {
                "source": source,
                "target": target,
                "weight": weight,
                "edge_type": "leaf_transition",
            }
        )

    return pd.DataFrame(split_rows), pd.DataFrame(leaf_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze ATP split summaries.")
    parser.add_argument(
        "--input_jsonl",
        required=True,
        help="Path to JSONL produced by single_child_growth.py or batch_run_atp.py",
    )
    parser.add_argument(
        "--out_dir",
        default="../temp/analysis",
        help="Directory for analysis CSV outputs",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    rows = load_jsonl(args.input_jsonl)
    print(f"Loaded {len(rows)} ATP run summaries from {args.input_jsonl}")

    # 1. First split analysis
    first_split_counts_df, first_split_most_common_df = most_common_first_split_by_stage(rows)
    first_split_counts_df.to_csv(
        os.path.join(args.out_dir, "stage_first_split_counts.csv"),
        index=False,
    )
    first_split_most_common_df.to_csv(
        os.path.join(args.out_dir, "stage_first_split_most_common.csv"),
        index=False,
    )

    # 2. Tree depth distribution
    depth_df = tree_depth_distribution(rows)
    depth_df.to_csv(
        os.path.join(args.out_dir, "tree_depth_distribution.csv"),
        index=False,
    )

    # 3. Productive leaf summary
    productive_df = productive_leaf_summary(rows)
    productive_df.to_csv(
        os.path.join(args.out_dir, "productive_leaf_summary.csv"),
        index=False,
    )

    # 4. Weighted split graph data
    split_edges_df, leaf_edges_df = build_weighted_split_edges(rows)
    split_edges_df.to_csv(
        os.path.join(args.out_dir, "weighted_split_edges.csv"),
        index=False,
    )
    leaf_edges_df.to_csv(
        os.path.join(args.out_dir, "weighted_leaf_edges.csv"),
        index=False,
    )

    print("\nSaved analysis files:")
    print(os.path.join(args.out_dir, "stage_first_split_counts.csv"))
    print(os.path.join(args.out_dir, "stage_first_split_most_common.csv"))
    print(os.path.join(args.out_dir, "tree_depth_distribution.csv"))
    print(os.path.join(args.out_dir, "productive_leaf_summary.csv"))
    print(os.path.join(args.out_dir, "weighted_split_edges.csv"))
    print(os.path.join(args.out_dir, "weighted_leaf_edges.csv"))


if __name__ == "__main__":
    main()