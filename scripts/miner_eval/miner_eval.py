import sys
import time
import itertools
from typing import Dict, List
import wandb 
import logging
import pandas as pd # type: ignore
import threading
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Define Run class
class RunClass:
    netuid = int
    def __init__(self, name: str, state: str, user: str):
        self.name = name
        self.state = state
        self.user = user
        self.final_scores = pd.DataFrame()

#Define Search Animation Function
def loading_animation(stop_event):
    chars = itertools.cycle(['-', '/', '|', '\\'])
    while not stop_event.is_set():
        sys.stdout.write('\rSearching ' + next(chars))
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 20 + '\r')  # Clear the line
    sys.stdout.flush()

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process validator runs for a specific hotkey/UID combo.')
    parser.add_argument('--uid', type=int, default=100, help='User ID (default: %(default)s)')
    parser.add_argument('--hotkey', type=str, default="5FLosL8CBXx2h4322UStUNoaX4uWLJdwG4Y7uNF3CRAc9H8y", help='Hotkey (default: %(default)s)')
    return parser.parse_args()

def fetch_runs(api: wandb.Api, project: str, entity: str) -> List[wandb.run]:
    """Fetch runs from WandB."""
    try:
        return api.runs(f"{entity}/{project}")
    except Exception as e:
        logger.error(f"Error fetching runs: {e}")
        return []

def process_runs(runs: List[wandb.run], uid: int, hotkey: str) -> pd.DataFrame:
    """Process runs and return a DataFrame of scores."""
    my_uid = uid
    my_hotkey = hotkey
    final_score_query_string=f"final_miner_score.{my_uid}"
    adjusted_score_query_string=f"adjusted_score.{my_uid}"
    hotkey_query_string= f"hotkey.{my_uid}"
    netuid_query_string=f"netuid"

    print(f"\nSearching Validator Runs for your Hotkey/UID Combo. This may take a few minutes.\n")
    print(f"UID: {my_uid}")
    print(f"Hotkey: {my_hotkey}\n")

    all_scores = []
    MyRuns=[]

    count = 0
    count_found = 0 

    stop_event = threading.Event()

    loading_thread = threading.Thread(target=loading_animation, args=(stop_event,))
    loading_thread.daemon = True
    loading_thread.start()

    for run in runs:
        name=run.name
        state=run.state
        user = run.user
        thisRun=RunClass(name,state,user)

        history = run.history(
            keys=[final_score_query_string,adjusted_score_query_string,hotkey_query_string]
            )

        if hotkey_query_string in history.columns:
            # Filter the history DataFrame
            filtered_history = history[history[hotkey_query_string] == my_hotkey]
            if not filtered_history.empty:
                thisRun.final_scores = filtered_history
                MyRuns.append(thisRun)
                count_found+=1
        
        count+=1

    stop_event.set()
    loading_thread.join()

    print(f"\nFound Hotkey/UID pair in {count_found} out of {count} runs\n")

    all_scores = []

    for thisrun in MyRuns:

        if not thisrun.final_scores.empty:
            thisrun.final_scores['run_name'] = thisrun.name
            thisrun.final_scores['username'] = thisrun.user.username
            
            all_scores.append(thisrun.final_scores)
        
        else:
            print(f"No data to display – Myruns empty. Likely mismatch of UID/Hotkey combo", file=sys.stderr)

    return pd.concat(all_scores, ignore_index=True) if all_scores else pd.DataFrame()


def analyze_scores(df: pd.DataFrame, uid: int) -> Dict[str, float]:
    """
    Analyze scores and return statistics.

    Args:
        df (pd.DataFrame): DataFrame containing the score data
        uid (int): User ID for column name construction

    Returns:
        Dict[str, float]: Dictionary containing various statistics
    """
    final_score_col = f"final_miner_score.{uid}"
    adjusted_score_col = f"adjusted_score.{uid}"

    # Ensure columns are numeric
    df[final_score_col] = pd.to_numeric(df[final_score_col], errors='coerce')
    df[adjusted_score_col] = pd.to_numeric(df[adjusted_score_col], errors='coerce')

    # Remove rows with NaN values
    df = df.dropna(subset=[final_score_col, adjusted_score_col])

    total_scores = len(df)
    
    if total_scores == 0:
        return {'error': 'No valid scores found after data cleaning'}

    mean_final_score = df[final_score_col].mean()
    mean_adjusted_score = df[adjusted_score_col].mean()

    # Avoid division by zero
    overall_penalty = ((mean_adjusted_score - mean_final_score) / mean_adjusted_score) if mean_adjusted_score != 0 else 0

    penalty_count = sum(df[final_score_col] < df[adjusted_score_col])
    penalty_percentage = (penalty_count / total_scores) * 100

    # Calculate mean score per run
    mean_scores_per_run = df.groupby('run_name')[final_score_col].mean()

    return {
        'total_scores': total_scores,
        'mean_final_score': mean_final_score,
        'mean_adjusted_score': mean_adjusted_score,
        'overall_penalty': overall_penalty,
        'penalty_count': penalty_count,
        'penalty_percentage': penalty_percentage,
        'mean_scores_per_run': mean_scores_per_run.to_dict(),
        'highest_score_run': mean_scores_per_run.idxmax(),
        'highest_score': mean_scores_per_run.max(),
        'lowest_score_run': mean_scores_per_run.idxmin(),
        'lowest_score': mean_scores_per_run.min()
    }

def pretty_print_stats(stats):
    print("Analysis results:")
    print("==================")
    
    # General stats
    print(f"Total scores: {stats['total_scores']}")
    print(f"Mean final score: {stats['mean_final_score']:.4f}")
    print(f"Mean adjusted score: {stats['mean_adjusted_score']:.4f}")
    print(f"Overall penalty: {stats['overall_penalty']:.4f}")
    print(f"Penalty count: {stats['penalty_count']}")
    print(f"Penalty percentage: {stats['penalty_percentage']:.2f}%")
    
    # Highest and lowest scores
    print(f"\nHighest scoring run: {stats['highest_score_run']}")
    print(f"Highest score: {stats['highest_score']:.4f}")
    print(f"Lowest scoring run: {stats['lowest_score_run']}")
    print(f"Lowest score: {stats['lowest_score']:.4f}")
    
    # Mean scores per run
    print("\nMean scores per run:")
    for run, score in sorted(stats['mean_scores_per_run'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {run}: {score:.4f}")


def main():
    args = parse_arguments()
    api = wandb.Api(timeout=180)
    runs = fetch_runs(api, "conversationgenome", "afterparty")
    scores_df = process_runs(runs, args.uid, args.hotkey)
    if not scores_df.empty:
        stats = analyze_scores(scores_df, args.uid)
        pretty_print_stats(stats)
    else:
        print("No data available for analysis. Please confirm UID/Hokey Pair")

if __name__ == "__main__":
    main()
    