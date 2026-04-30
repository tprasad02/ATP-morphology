"""
plot_meta_tree.py

Draw a weighted meta-tree / meta-graph from ATP split analysis.

Input:
This script reads:
    - weighted_split_edges.csv
    - weighted_leaf_edges.csv
which are produced by analyze_splits.py.

Output:
A PDF showing:
    - split transitions
    - leaf-rule transitions
    - weights on each edge

This gives us a visualization of aggregate ATP behavior across runs,
without pretending all trees are literally identical.

From src/:

    python plot_meta_tree.py \
        --split_edges ../temp/analysis/weighted_split_edges.csv \
        --leaf_edges ../temp/analysis/weighted_leaf_edges.csv \
        --out ../temp/analysis/meta_tree
"""

from __future__ import annotations

import argparse
import os
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot a weighted ATP meta-tree.")
    parser.add_argument(
        "--split_edges",
        required=True,
        help="CSV from analyze_splits.py containing split-transition edges",
    )
    parser.add_argument(
        "--leaf_edges",
        required=True,
        help="CSV from analyze_splits.py containing leaf-transition edges",
    )
    parser.add_argument(
        "--out",
        default="../temp/analysis/meta_tree",
        help="Output prefix for Graphviz render",
    )
    args = parser.parse_args()


    from graphviz import Digraph

    split_df = pd.read_csv(args.split_edges)
    leaf_df = pd.read_csv(args.leaf_edges)

    dot = Digraph(comment="ATP Weighted Meta-Tree")
    dot.attr(rankdir="LR")

    seen_nodes = set()

    def add_node_if_needed(node_name: str, is_leaf_rule: bool = False) -> None:
        """
        Add a node once, with a shape depending on its role.
        """
        if node_name in seen_nodes:
            return
        seen_nodes.add(node_name)

        if node_name == "ROOT":
            dot.node(node_name, shape="circle")
        elif is_leaf_rule:
            dot.node(node_name, shape="box")
        else:
            dot.node(node_name, shape="ellipse")

    # Add split-transition edges
    for _, row in split_df.iterrows():
        source = str(row["source"])
        target = str(row["target"])
        weight = int(row["weight"])

        add_node_if_needed(source, is_leaf_rule=False)
        add_node_if_needed(target, is_leaf_rule=False)

        dot.edge(source, target, label=str(weight))

    # Add final split -> leaf-rule edges
    for _, row in leaf_df.iterrows():
        source = str(row["source"])
        target = str(row["target"])
        weight = int(row["weight"])

        add_node_if_needed(source, is_leaf_rule=False)
        add_node_if_needed(target, is_leaf_rule=True)

        dot.edge(source, target, label=str(weight))

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    rendered_path = dot.render(args.out, format="pdf", cleanup=True)
    print(f"Saved weighted meta-tree to: {rendered_path}")


if __name__ == "__main__":
    main()