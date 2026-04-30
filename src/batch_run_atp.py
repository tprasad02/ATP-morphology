"""
batch_run_atp.py

Run ATP over MANY child/stage files and save structured summaries.

Architecture:
This script intentionally reuses baseline_run.run_one_file()
rather than duplicating ATP loading/training/summary logic.
    - baseline_run.py is the single source of truth for one-file runs
    - this script is just a loop over children and growth sizes

For each requested child/stage combination:
    1. loads the file
    2. runs ATP using baseline_run.run_one_file()
    3. writes one JSON summary line to an output JSONL file
    4. optionally saves one tree PDF per run

From src/:

    python batch_run_atp.py \
        --root ../data/english/growth \
        --children 0 1 2 3 4 \
        --sizes 50 100 200 500 1000 \
        --sep " " \
        --use_ipa true \
        --out_jsonl ../temp/batch_runs.jsonl \
        --save_trees false
"""

from __future__ import annotations

import argparse
import json
import os

from baseline_run import run_one_file, str2bool


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run baseline ATP over multiple children and growth sizes."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Path to English growth root directory.",
    )
    parser.add_argument(
        "--children",
        nargs="+",
        type=int,
        required=True,
        help="Child IDs to run, e.g. 0 1 2 3 4",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        required=True,
        help="Growth sizes to run, e.g. 50 100 200 500 1000",
    )
    parser.add_argument(
        "--sep",
        default=" ",
        help="Separator for load_pairs().",
    )
    parser.add_argument(
        "--use_ipa",
        type=str2bool,
        default=True,
        help="Whether to convert orthography to IPA.",
    )
    parser.add_argument(
        "--out_jsonl",
        default="../temp/batch_runs.jsonl",
        help="Path to JSONL summary output.",
    )
    parser.add_argument(
        "--save_trees",
        type=str2bool,
        default=False,
        help="Whether to save one PDF tree per run.",
    )
    parser.add_argument(
        "--tree_dir",
        default="../temp/batch_trees",
        help="Directory for saved tree PDFs.",
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_jsonl), exist_ok=True)
    if args.save_trees:
        os.makedirs(args.tree_dir, exist_ok=True)

    run_count = 0

    with open(args.out_jsonl, "w", encoding="utf-8") as out_f:
        for child_id in args.children:
            for growth_size in args.sizes:
                input_path = os.path.join(
                    args.root,
                    f"child-{child_id}",
                    f"{growth_size}.txt",
                )

                if not os.path.exists(input_path):
                    print(f"Skipping missing file: {input_path}")
                    continue

                tree_out = None
                if args.save_trees:
                    tree_out = os.path.join(
                        args.tree_dir,
                        f"child{child_id}_{growth_size}"
                    )

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
                    f"Finished child-{child_id} size={growth_size} | "
                    f"pairs={summary['num_pairs']} | "
                    f"leaves={summary['num_leaves']} | "
                    f"depth={summary['tree_depth']} | "
                    f"first_split={summary['first_split']}"
                )

    print(f"\nSaved {run_count} summaries to: {args.out_jsonl}")


if __name__ == "__main__":
    main()