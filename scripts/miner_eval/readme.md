# Validator Run Analyzer

This script analyzes validator runs for a specific hotkey/UID combination in the ConversationGenome project on Weights & Biases.

## Prerequisites

- Python 3.7+
- pip (Python package installer)

## Installation

1. Clone this repository or download the script.
2. Install the required packages:
    `pip install -r requirements.txt`

## Usage

Run the script using Python:

`python miner_eval.py [--uid UID] [--hotkey HOTKEY]`

Arguments:
- `--uid`: User ID (default: 100)
- `--hotkey`: Hotkey (default: "5FLosL8CBXx2h4322UStUNoaX4uWLJdwG4Y7uNF3CRAc9H8y")

Example:
python validator_run_analyzer.py --uid 129 --hotkey 5GZXMRGH4QvMMzN4C3eb8G5cvJyGebYaeXhy14cvDEksuXdm

If no arguments are provided, the script will use the default values.

## Output

The script will display:
- Total number of scores
- Overall mean score
- Overall penalty
- Number and percentage of penalties
- Mean score per run