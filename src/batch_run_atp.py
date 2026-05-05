"""
batch_run_atp.py

Run ATP across multiple simulated children and multiple lexicon sizes.

At a given lexicon size, do independently sampled child lexicons produce the
same exact productive ATP rule paths?

Outputs:
1. batch_summary.csv
   One row per child/lexicon-size run.

2. batch_leaf_paths.csv
   One row per ATP leaf.

3. batch_productive_rules.csv
   One row per productive ATP rule.

This script does not count how often local split labels occur. Children are
trained on different sampled lexicons, so branch frequencies are not directly
interpretable as acquisition frequencies. The comparison unit is instead the
exact full productive rule signature.

Example run:
from src
python batch_run_atp.py \
  --root ../data/english/growth \
  --children 0 1 2 3 4 \
  --sizes 50 100 200 500 1000 \
  --sep " " \
  --use_ipa true \
  --out_dir ../temp/batch_rule_paths
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List

from baseline_run import run_one_file, str2bool


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]) -> None:
    """Write rows to a CSV file, creating output directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def leaf_to_row(child_id: int, size: int, leaf_index: int, leaf: Dict) -> Dict:
    """Convert one ATP leaf into a flat CSV row."""
    return {
        "child_id": child_id,
        "lexicon_size": size,
        "leaf_index": leaf_index,
        "productive": leaf["productive"],
        "depth": leaf["depth"],
        "conditions": leaf["conditions"],
        "rule": leaf["rule"],
        "rule_signature": leaf["rule_signature"],
        "path_ordered": " > ".join(leaf["path"]),
        "leaf_name": leaf["leaf_name"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ATP across children and lexicon sizes.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--children", nargs="+", type=int, required=True)
    parser.add_argument("--sizes", nargs="+", type=int, required=True)
    parser.add_argument("--sep", default=" ")
    parser.add_argument("--use_ipa", type=str2bool, default=True)
    parser.add_argument("--out_dir", default="../temp/batch_rule_paths")
    parser.add_argument("--save_trees", type=str2bool, default=False)
    parser.add_argument("--tree_dir", default="../temp/batch_trees")

    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if args.save_trees:
        os.makedirs(args.tree_dir, exist_ok=True)

    summary_rows: List[Dict] = []
    leaf_rows: List[Dict] = []
    productive_rows: List[Dict] = []

    for child_id in args.children:
        for size in args.sizes:
            input_path = os.path.join(args.root, f"child-{child_id}", f"{size}.txt")

            if not os.path.exists(input_path):
                print(f"Skipping missing file: {input_path}")
                continue

            tree_out = None
            if args.save_trees:
                tree_out = os.path.join(args.tree_dir, f"child{child_id}_{size}")

            summary = run_one_file(
                input_path=input_path,
                sep=args.sep,
                use_ipa=args.use_ipa,
                tree_out=tree_out,
                child_id=child_id,
                lexicon_size=size,
            )

            summary_rows.append(
                {
                    "child_id": child_id,
                    "lexicon_size": size,
                    "input_path": input_path,
                    "num_leaves": summary["num_leaves"],
                    "num_productive_leaves": summary["num_productive_leaves"],
                    "num_nonproductive_leaves": summary["num_nonproductive_leaves"],
                    "tree_depth": summary["tree_depth"],
                    "tree_pdf": summary["tree_pdf"],
                }
            )

            for i, leaf in enumerate(summary["leaf_paths"]):
                row = leaf_to_row(child_id, size, i, leaf)
                leaf_rows.append(row)

                if leaf["productive"]:
                    productive_rows.append(row)

            print(
                f"Finished child-{child_id} size={size} | "
                f"leaves={summary['num_leaves']} | "
                f"productive={summary['num_productive_leaves']} | "
                f"nonproductive={summary['num_nonproductive_leaves']} | "
                f"depth={summary['tree_depth']}"
            )

    summary_fields = [
        "child_id",
        "lexicon_size",
        "input_path",
        "num_leaves",
        "num_productive_leaves",
        "num_nonproductive_leaves",
        "tree_depth",
        "tree_pdf",
    ]

    leaf_fields = [
        "child_id",
        "lexicon_size",
        "leaf_index",
        "productive",
        "depth",
        "conditions",
        "rule",
        "rule_signature",
        "path_ordered",
        "leaf_name",
    ]

    write_csv(os.path.join(args.out_dir, "batch_summary.csv"), summary_rows, summary_fields)
    write_csv(os.path.join(args.out_dir, "batch_leaf_paths.csv"), leaf_rows, leaf_fields)
    write_csv(os.path.join(args.out_dir, "batch_productive_rules.csv"), productive_rows, leaf_fields)

    print(f"\nSaved batch outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()