# ATP Rule Path Stability Analysis

## Overview

This project extends the ATP morphology codebase from:

**Belth et al. (2021), _The Greedy and Recursive Search for Morphological Productivity_**

The original repository implements ATP. This project does not modify ATP itself. Instead, it adds an analysis pipeline that runs ATP across simulated child lexicons and studies the stability of the rules ATP learns.

---

## Research Questions

1. **Within-child stability**  
   As one simulated child’s lexicon grows, do productive rule paths persist or change?

2. **Across-child variation**  
   At the same lexicon size, do different simulated children learn the same rule paths?

3. **Tree complexity across growth**  
   How does ATP tree depth and productivity change as lexicon size increases?

---

## Method

ATP learns a decision tree. In this project, a rule is compared using its full path through the tree plus the final suffix rule.

Example:
¬PRS & PST & k# => inflected = lemma + t

This project compares these full rule signatures, not individual tree splits. This is important because each simulated child is trained on a different sampled lexicon. Therefore, counting how often ATP splits on a feature such as `PST` or `PL` can be misleading: split frequencies may reflect differences in input data rather than differences in learning.

---

## Code Structure

All analysis code is located in:
analysis/

### `io_utils.py`
Shared helper functions for writing JSON and CSV files.

---

### `baseline_run.py`
Runs ATP on one lexicon and extracts learned rule paths.

Outputs:

baseline_summary.json
baseline_rules.csv
(optional) tree PDF if --tree_out is provided

---

### `single_child_growth.py`
Runs ATP across multiple lexicon sizes for one simulated child.

Outputs:

single_child_summary.csv
single_child_rules.csv

---

### `batch_run_atp.py`
Runs ATP across multiple simulated children and multiple lexicon sizes.

Outputs:

batch_summary.csv
batch_rules.csv

---

### `analyze_rules.py`
Analyzes the outputs from `batch_run_atp.py`.

Outputs:

complexity_by_size.csv
within_child_rule_overlap.csv
cross_child_rule_recurrence.csv
rule_path_analysis_summary.txt

---

## Setup

Use the setup instructions in the original ATP README for installing ATP and its dependencies.

Run all commands from the repository root. Make sure Python can find the ATP code in `src/`:

bash
export PYTHONPATH=src
Running the Project

Run the steps in this order:

1. Baseline
PYTHONPATH=src python analysis/baseline_run.py \
  --input data/english/growth/child-0/500.txt \
  --child_id 0 \
  --lexicon_size 500 \
  --use_ipa true \
  --tree_out temp/child0_500 \
  --open_pdf false

2. Single-child growth
PYTHONPATH=src python analysis/single_child_growth.py \
  --root data/english/growth \
  --child_id 0 \
  --sizes 50 100 200 500 800 1000 \
  --use_ipa true \
  --out_dir temp/single_child_rule_paths \
  --save_trees true \
  --tree_dir temp/single_child_trees

3. Batch run across children (main experiment)

Example with 5 children:

PYTHONPATH=src python analysis/batch_run_atp.py \
  --root data/english/growth \
  --children 0 1 2 3 4 \
  --sizes 50 100 200 500 800 1000 \
  --use_ipa true \
  --out_dir temp/batch_rule_paths \
  --save_trees false

Example with 100 children:

PYTHONPATH=src python analysis/batch_run_atp.py \
  --root data/english/growth \
  --children $(seq 0 99) \
  --sizes 50 100 200 500 800 1000 \
  --use_ipa true \
  --out_dir temp/batch_rule_paths_100children \
  --save_trees false

4. Analyze results
PYTHONPATH=src python analysis/analyze_rules.py \
  --summary_csv temp/batch_rule_paths_100children/batch_summary.csv \
  --rules_csv temp/batch_rule_paths_100children/batch_rules.csv \
  --out_dir temp/rule_analysis_100children \
  --interesting_threshold 0.3

---

## Main Output Files

After running the analysis:

temp/rule_analysis_100children/rule_path_analysis_summary.txt

temp/rule_analysis_100children/complexity_by_size.csv

temp/rule_analysis_100children/within_child_rule_overlap.csv

temp/rule_analysis_100children/cross_child_rule_recurrence.csv

---

## Notes

- The English growth files are simulated child lexicons, not raw child transcripts.
- Different simulated children receive different sampled lexicons.
- The main unit of comparison is the exact productive rule signature.

---

## Summary

This project shows that ATP rule learning is:
- Unstable at early lexicon sizes
- More complex at intermediate stages
- Simpler and more general at larger sizes

Differences between learners largely reflect differences in input data rather than differences in the learning process.