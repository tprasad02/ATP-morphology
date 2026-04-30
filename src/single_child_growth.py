"""
single_child_growth.py

Run the same baseline ATP procedure over multiple growth files
for a single child.

Architecture:
This script intentionally reuses baseline_run.run_one_file()
rather than duplicating ATP loading/training/summary logic.
    - baseline_run.py is the single source of truth for one-file runs
    - this script loops over growth sizes

From src/:

    python single_child_growth.py \
        --root ../data/english/growth \
        --child 0 \
        --sizes 50 100 150 200 500 1000 \
        --sep " " \
        --use_ipa true \
        --out_jsonl ../temp/child0_growth.jsonl \
        --save_trees true \
        --tree_dir ../temp/child0_trees
"""

from __future__ import annotations

import argparse
import json
import os

from baseline_run import run_one_file, str2bool


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run baseline ATP over multiple growth sizes for one child."
    )
    parser.add_argument("--root", required=True, help="Path to english growth root directory.")
    parser.add_argument("--child", type=int, required=True, help="Child ID to analyze.")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        required=True,
        help="Growth sizes to run, e.g. 50 100 150 200 500 1000",
    )
    parser.add_argument("--sep", default=" ", help="Separator for load_pairs().")
    parser.add_argument(
        "--use_ipa",
        type=str2bool,
        default=True,
        help="Whether to convert orthography to IPA.",
    )
    parser.add_argument(
        "--out_jsonl",
        default="../temp/single_child_growth.jsonl",
        help="Path to JSONL summary output.",
    )
    parser.add_argument(
        "--save_trees",
        type=str2bool,
        default=True,
        help="Whether to save one PDF tree per growth size.",
    )
    parser.add_argument(
        "--tree_dir",
        default="../temp/single_child_trees",
        help="Directory for saved tree PDFs.",
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_jsonl), exist_ok=True)
    if args.save_trees:
        os.makedirs(args.tree_dir, exist_ok=True)

    run_count = 0

    with open(args.out_jsonl, "w", encoding="utf-8") as out_f:
        for growth_size in args.sizes:
            input_path = os.path.join(
                args.root,
                f"child-{args.child}",
                f"{growth_size}.txt",
            )

            if not os.path.exists(input_path):
                print(f"Skipping missing file: {input_path}")
                continue

            tree_out = None
            if args.save_trees:
                tree_out = os.path.join(args.tree_dir, f"child{args.child}_{growth_size}")

            summary = run_one_file(
                input_path=input_path,
                sep=args.sep,
                use_ipa=args.use_ipa,
                tree_out=tree_out,
                open_pdf=False,
            )

            out_f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            run_count += 1

            print(
                f"Finished child-{args.child} size={growth_size} | "
                f"pairs={summary['num_pairs']} | "
                f"leaves={summary['num_leaves']} | "
                f"depth={summary['tree_depth']} | "
                f"first_split={summary['first_split']}"
            )

    print(f"\nSaved {run_count} summaries to: {args.out_jsonl}")


if __name__ == "__main__":
    main()