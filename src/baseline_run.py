"""
baseline_run.py

Run ATP on a single dataset file, save a tree, inspect the learned leaves,
and expose reusable helper functions for other scripts.

This file is designed to serve two roles:
1. Standalone script:
   It can be run directly on one file to establish a baseline.

2. Reusable module:
   Other scripts (for example single_child_growth.py or batch_run_atp.py)
   can import run_one_file() instead of duplicating ATP training logic.

From the src/ directory:

    python baseline_run.py \
        --input ../data/english/growth/child-0/100.txt \
        --sep " " \
        --use_ipa true \
        --tree_out ../temp/child0_100 \
        --summary_out ../temp/child0_100_summary.txt \
        --json_out ../temp/child0_100_summary.json

Notes
- For English growth data, sep=" " is typically correct.
- If use_ipa=true, orthographic forms are mapped to IPA using load_word_to_ipa().
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Tuple, Optional

from atp import ATP
from utils import load_pairs, load_word_to_ipa


def str2bool(value: str) -> bool:
    """
    Convert common string booleans into actual booleans.
    """
    value = value.lower()
    if value in {"true", "t", "1", "yes", "y"}:
        return True
    if value in {"false", "f", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected a boolean value.")


def is_leaf_productive(leaf) -> bool:
    """
    Decide whether an ATP leaf is productive.

    ATP leaf nodes typically have a switch_statement.productive attribute.
    """
    try:
        return bool(leaf.switch_statement.productive)
    except Exception:
        return "No Productive Process" not in leaf.name


def get_rule_string_from_leaf_name(leaf_name: str) -> str:
    """
    Extract the rule portion from a leaf name.

    Example:
        'PRS => inflected = lemma + ɪŋ'
    returns:
        'inflected = lemma + ɪŋ'
    """
    if "=>" in leaf_name:
        return leaf_name.split("=>", 1)[1].strip()
    return leaf_name.strip()


def compute_tree_depth(node) -> int:
    """
    Compute the maximum depth of an ATP tree recursively.

    Convention:
        - a leaf has depth 0
        - a root with one split below it has depth 1
    """
    if node.num_children() == 0:
        return 0
    return 1 + max(compute_tree_depth(child) for _, child in node.get_children())


def extract_root_split(atp_model) -> str:
    """
    Extract the first split feature at the root of the ATP tree.

    Returns:
        String name of the split feature, or 'NO_CHILDREN' if no split exists.
    """
    root = atp_model.root
    children = root.get_children()
    if not children:
        return "NO_CHILDREN"

    branch_condition, _child = children[0]
    _pos, split_feature = branch_condition
    return str(split_feature)


def traverse_tree_paths(node, path_prefix=None) -> List[Dict[str, Any]]:
    """
    Traverse the ATP tree and collect root-to-leaf paths.

    Each returned dict contains:
        - path: list of signed split labels, e.g. ['PRS', '¬PL']
        - leaf_name
        - productive
        - rule
        - depth

    This is useful both for single baselines and later aggregate analyses.
    """
    if path_prefix is None:
        path_prefix = []

    results = []

    if node.num_children() == 0:
        results.append(
            {
                "path": path_prefix,
                "leaf_name": node.name,
                "productive": is_leaf_productive(node),
                "rule": get_rule_string_from_leaf_name(node.name),
                "depth": len(path_prefix),
            }
        )
        return results

    for branch_condition, child in node.get_children():
        pos, split_feature = branch_condition
        signed_label = str(split_feature) if pos else f"¬{split_feature}"
        results.extend(traverse_tree_paths(child, path_prefix + [signed_label]))

    return results


def load_training_pairs(
    input_path: str,
    sep: str = " ",
    use_ipa: bool = True,
) -> Tuple[List[Tuple[str, str, Tuple[str, ...]]], Any]:
    """
    Load one dataset file and return (pairs, feature_space).

    If use_ipa=True, orthographic forms are mapped to IPA using Belth's helper.
    """
    preprocessing = None
    if use_ipa:
        word_to_ipa = load_word_to_ipa()
        preprocessing = lambda s: word_to_ipa[s]

    pairs, feature_space = load_pairs(
        input_path,
        sep=sep,
        preprocessing=preprocessing,
    )
    return pairs, feature_space


def build_summary(
    input_path: str,
    pairs: List[Tuple[str, str, Tuple[str, ...]]],
    feature_space,
    atp_model,
) -> Dict[str, Any]:
    """
    Build a structured summary dictionary for one ATP run.
    """
    leaf_paths = traverse_tree_paths(atp_model.root)
    num_productive = sum(1 for leaf in leaf_paths if leaf["productive"])
    num_nonproductive = len(leaf_paths) - num_productive

    return {
        "input_path": input_path,
        "num_pairs": len(pairs),
        "feature_space": sorted(feature_space),
        "num_leaves": len(leaf_paths),
        "num_productive_leaves": num_productive,
        "num_nonproductive_leaves": num_nonproductive,
        "tree_depth": compute_tree_depth(atp_model.root),
        "first_split": extract_root_split(atp_model),
        "leaf_paths": leaf_paths,
    }


def write_text_summary(summary: Dict[str, Any], out_path: str) -> None:
    """
    Write a text summary to file.
    """
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Loaded: {summary['input_path']}\n")
        f.write(f"Number of pairs: {summary['num_pairs']}\n")
        f.write(f"Feature space: {summary['feature_space']}\n")
        f.write(f"Number of leaves: {summary['num_leaves']}\n")
        f.write(f"Productive leaves: {summary['num_productive_leaves']}\n")
        f.write(f"Non-productive leaves: {summary['num_nonproductive_leaves']}\n")
        f.write(f"Tree depth: {summary['tree_depth']}\n")
        f.write(f"First split: {summary['first_split']}\n")
        f.write("\nLeaves:\n")
        for leaf in summary["leaf_paths"]:
            f.write(
                f"- productive={leaf['productive']} | "
                f"depth={leaf['depth']} | "
                f"rule={leaf['rule']} | "
                f"path={leaf['path']} | "
                f"name={leaf['leaf_name']}\n"
            )


def run_one_file(
    input_path: str,
    sep: str = " ",
    use_ipa: bool = True,
    tree_out: Optional[str] = None,
    open_pdf: bool = False,
) -> Dict[str, Any]:
    """
    Core reusable ATP runner for ONE file.

    Parameters
    ----------
    input_path:
        Path to the dataset file.
    sep:
        Column separator for load_pairs().
    use_ipa:
        Whether to map orthographic forms to IPA.
    tree_out:
        If provided, save a PDF tree to this prefix.
        Example: '../temp/child0_100' -> '../temp/child0_100.pdf'
    open_pdf:
        Whether to auto-open the saved PDF.

    Returns
    -------
    summary : dict
        Structured summary of the ATP run.
    """
    pairs, feature_space = load_training_pairs(
        input_path=input_path,
        sep=sep,
        use_ipa=use_ipa,
    )

    atp_model = ATP(
        apply_phonology=use_ipa,
        feature_space=feature_space,
    ).train(pairs)

    summary = build_summary(
        input_path=input_path,
        pairs=pairs,
        feature_space=feature_space,
        atp_model=atp_model,
    )

    if tree_out is not None:
        atp_model.plot_tree(tree_out, open_pdf=open_pdf)
        summary["tree_pdf"] = f"{tree_out}.pdf"
    else:
        summary["tree_pdf"] = None

    return summary


def main() -> None:
    """
    Standalone CLI entry point for one-file baseline runs.
    """
    parser = argparse.ArgumentParser(description="Run one ATP baseline.")
    parser.add_argument("--input", "-i", required=True, help="Path to training file.")
    parser.add_argument("--sep", default=" ", help="Column separator for load_pairs().")
    parser.add_argument(
        "--use_ipa",
        type=str2bool,
        default=True,
        help="If true, map English orthography to IPA.",
    )
    parser.add_argument(
        "--tree_out",
        default="../temp/baseline_tree",
        help="Prefix for saved tree PDF.",
    )
    parser.add_argument(
        "--summary_out",
        default="../temp/baseline_summary.txt",
        help="Path to text summary output.",
    )
    parser.add_argument(
        "--json_out",
        default="../temp/baseline_summary.json",
        help="Path to JSON summary output.",
    )
    parser.add_argument(
        "--open_pdf",
        type=str2bool,
        default=False,
        help="If true, auto-open the tree PDF.",
    )
    args = parser.parse_args()

    summary = run_one_file(
        input_path=args.input,
        sep=args.sep,
        use_ipa=args.use_ipa,
        tree_out=args.tree_out,
        open_pdf=args.open_pdf,
    )

    write_text_summary(summary, args.summary_out)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    if summary["tree_pdf"] is not None:
        print(f"\nSaved tree to: {summary['tree_pdf']}")
    print(f"Saved text summary to: {args.summary_out}")
    print(f"Saved JSON summary to: {args.json_out}")


if __name__ == "__main__":
    main()