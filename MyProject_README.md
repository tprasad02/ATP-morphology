# Extension Project: ATP Split Stability Analysis

## Overview

This repository is a fork of the ATP morphology codebase from:

**Belth, Caleb, Sarah Payne, Deniz Beser, Jordan Kodner, and Charles Yang. 2021. _The Greedy and Recursive Search for Morphological Productivity._ CogSci.**

The original repository implements **ATP (Abduction of Tolerable Productivity)**, a model that learns morphological rules by recursively searching for productive patterns in a lexicon.

This extension project does not change ATP’s learning algorithm itself. Instead, it builds an **analysis pipeline on top of ATP** to study how stable ATP’s learned decision tree structure is across simulated child lexicons.

More specifically, this project asks:

- What is the most common **first split** ATP makes at a given lexicon size?
- How does **tree depth** change across growth stages?
- How many **productive leaves** appear in different runs?
- What split patterns recur across children and growth stages?
- Can those recurring patterns be summarized in a **weighted aggregate meta-tree**?

## What is original vs. new

### Original Belth repository
The following are original to the ATP repository:
- ATP model implementation
- recursive search algorithm
- English growth data
- core utilities
- original experiments and tests

### My extension

Belth et al.’s original ATP code learns morphology from one lexicon at a time.
This extension adds an **analysis layer across ATP runs**. It makes it possible to study:

- split stability across child-sized lexicons
- common first splits at different growth stages
- variation in tree depth
- productive rule counts
- aggregate split structure

- `baseline_run.py`
  - run ATP on one file and save a tree and summaries

- `single_child_growth.py`
  - run ATP across all requested growth stages for one child

- `batch_run_atp.py`
  - run ATP across multiple children and multiple growth stages

- `analyze_splits.py`
  - read saved ATP summaries and compute aggregate statistics

- `plot_meta_tree.py`
  - draw a weighted aggregate split graph from the analysis outputs

## Repository scripts

### 1. `baseline_run.py`
Run ATP on **one dataset file**.

It:
- loads one file
- trains ATP
- extracts a structured summary
- optionally saves one tree PDF
- optionally saves text and JSON summaries

Use this to establish your baseline.

### 2. `single_child_growth.py`
Run ATP for **one child across multiple growth sizes**.

It:
- loops over files like `child-0/50.txt`, `child-0/100.txt`, etc.
- runs ATP on each
- saves one JSON summary line per run
- optionally saves one tree PDF per growth stage

Use this for the **within-child developmental analysis**.

### 3. `batch_run_atp.py`
Run ATP across **multiple children and multiple growth sizes**.

It:
- loops over selected child IDs and growth sizes
- runs ATP on each file
- saves one JSON summary line per run
- optionally saves one tree PDF per run

Use this for the **cross-child comparison**.

### 4. `analyze_splits.py`
Read the JSON summaries and compute aggregate analyses.

It produces:
- first split counts by growth stage
- most common first split by growth stage
- tree depth distributions
- productive leaf summaries
- weighted split-transition edge data
- weighted leaf-transition edge data

Use this after running `single_child_growth.py` or `batch_run_atp.py`.

### 5. `plot_meta_tree.py`
Read the weighted edge CSV files and draw an aggregate **weighted meta-tree**.

It produces:
- a PDF graph showing split transitions and leaf-rule transitions
- edge labels show how often that transition occurred across ATP runs

Use this after running `analyze_splits.py`.

## Directory assumptions

These instructions assume:

- you are running commands from the **`src/`** directory
- the English growth data are in:
../data/english/growth/

- temporary outputs are written to:
../temp/

## Setup

### 1. Install ATP
From the repository root:

```bash
python setup.py
```

### 2. Test ATP installation
From the repository root:

```bash
cd test
python tester.py
```

If `tester.py` runs successfully, ATP is installed correctly.

## Graphviz setup

Graphviz is required for saving ATP trees as PDFs and for plotting the aggregate meta-tree.

### Python package
Install the Python wrapper:

```bash
python -m pip install graphviz
```

### System package on Mac
Install Graphviz itself:

```bash
brew install graphviz
```

### Test Graphviz import
From `src/`:

```bash
python -c "import graphviz; print('graphviz OK')"
```

## Recommended workflow

### Step 1: establish the baseline
Run:

```bash
python baseline_run.py \
  --input ../data/english/growth/child-0/100.txt \
  --sep " " \
  --use_ipa true \
  --tree_out ../temp/child0_100 \
  --summary_out ../temp/child0_100_summary.txt \
  --json_out ../temp/child0_100_summary.json
```

### Step 2: run one child across growth stages
Run:

```bash
python single_child_growth.py \
  --root ../data/english/growth \
  --child 0 \
  --sizes 50 100 150 200 500 1000 \
  --sep " " \
  --use_ipa true \
  --out_jsonl ../temp/child0_growth.jsonl \
  --save_trees true \
  --tree_dir ../temp/child0_trees
```

### Step 3: run multiple children at selected stages
Run:

```bash
python batch_run_atp.py \
  --root ../data/english/growth \
  --children 0 1 2 3 4 \
  --sizes 100 500 1000 \
  --sep " " \
  --use_ipa true \
  --out_jsonl ../temp/batch_runs.jsonl \
  --save_trees false
```

### Step 4: analyze split trends
Run:

```bash
python analyze_splits.py \
  --input_jsonl ../temp/batch_runs.jsonl \
  --out_dir ../temp/analysis
```

### Step 5: visualize the aggregate structure
Run:

```bash
python plot_meta_tree.py \
  --split_edges ../temp/analysis/weighted_split_edges.csv \
  --leaf_edges ../temp/analysis/weighted_leaf_edges.csv \
  --out ../temp/analysis/meta_tree
```

## Notes

- The English growth files are **simulated child lexicons**, not raw CHILDES transcripts.
- “Children” in this project refer to separate simulated lexicon samples in the ATP repository.
- The weighted meta-tree is an aggregate visualization of repeated ATP behavior, not a literal transducer or one learner’s grammar.
- For English growth data, `--use_ipa true` is recommended because Belth’s English experiments are phonology-aware.
