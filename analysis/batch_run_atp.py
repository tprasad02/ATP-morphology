"""
batch_run_atp.py

Run ATP across multiple simulated children and multiple lexicon sizes.

Outputs:
- batch_summary.csv
- batch_rules.csv

Example:
PYTHONPATH=src python analysis/batch_run_atp.py \
  --root data/english/growth \
  --children 0 1 2 3 4 \
  --sizes 50 100 200 500 800 1000 \
  --use_ipa true \
  --out_dir temp/batch_rule_paths \
  --save_trees false
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List

from baseline_run import RULE_FIELDS, SUMMARY_FIELDS, rule_rows, run_one_file, str2bool, summary_for_output
from io_utils import write_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run ATP across multiple children and lexicon sizes."
    )

    parser.add_argument("--root", required=True)
    parser.add_argument("--children", nargs="+", type=int, required=True)
    parser.add_argument("--sizes", nargs="+", type=int, required=True)
    parser.add_argument("--sep", default=" ")
    parser.add_argument("--use_ipa", type=str2bool, default=True)
    parser.add_argument("--out_dir", default="temp/batch_rule_paths")
    parser.add_argument("--save_trees", type=str2bool, default=False)
    parser.add_argument("--tree_dir", default="temp/batch_trees")

    args = parser.parse_args()

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    if args.save_trees:
        Path(args.tree_dir).mkdir(parents=True, exist_ok=True)

    summary_rows: List[Dict[str, Any]] = []
    rules_rows: List[Dict[str, Any]] = []

    for child_id in args.children:
        for lexicon_size in args.sizes:
            input_path = os.path.join(args.root, f"child-{child_id}", f"{lexicon_size}.txt")

            if not os.path.exists(input_path):
                print(f"Skipping missing file: {input_path}")
                continue

            tree_out = None
            if args.save_trees:
                tree_out = os.path.join(args.tree_dir, f"child{child_id}_{lexicon_size}")

            summary = run_one_file(
                input_path=input_path,
                sep=args.sep,
                use_ipa=args.use_ipa,
                tree_out=tree_out,
                open_pdf=False,
                child_id=child_id,
                lexicon_size=lexicon_size,
            )

            summary_rows.append(summary_for_output(summary))
            rules_rows.extend(rule_rows(summary))

            print(
                f"Finished child-{child_id} size={lexicon_size} | "
                f"rules={summary['num_rules']} | "
                f"productive={summary['num_productive_rules']} | "
                f"nonproductive={summary['num_nonproductive_rules']} | "
                f"depth={summary['tree_depth']}"
            )

    write_csv(os.path.join(args.out_dir, "batch_summary.csv"), summary_rows, SUMMARY_FIELDS)
    write_csv(os.path.join(args.out_dir, "batch_rules.csv"), rules_rows, RULE_FIELDS)

    print(f"\nSaved batch outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()