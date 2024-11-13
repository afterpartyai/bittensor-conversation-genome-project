import time
import os
from constants import *

from Utils import Utils
from Db import Db
from huggingface_hub import HfApi, hf_hub_download
import re


class PreprocessorLib():
    db = None
    JOB_STATUS_QUEUED =  1
    JOB_STATUS_TASKED =  2
    JOB_STATUS_DONE =  3
    JOB_STATUS_PAUSED =  4
    JOB_STATUS_DELETED =  10
    JOB_STATUS_ARCHIVED =  11
    JOB_STATUS_ERROR_PATH =  90
    JOB_STATUS_ERROR_DATA_SOURCE =  91
    JOB_STATUS_ERROR_PROMPT =  92
    JOB_STATUS_ERROR_EMPTY_PATH =  93

    JOB_STATUS_DICT = {}

    JOB_DATA_SOURCE_LOCAL = 1
    JOB_DATA_SOURCE_HUGGING_FACE = 2
    JOB_DATA_SOURCE_ONEDRIVE = 3

    def __init__(self):
        self.JOB_STATUS_DICT = {
            self.JOB_STATUS_QUEUED: 'Queued',
            self.JOB_STATUS_TASKED: 'In progress',
            self.JOB_STATUS_DONE: 'Complete',
            self.JOB_STATUS_PAUSED: 'Paused',
            self.JOB_STATUS_DELETED: 'Deleted',
            self.JOB_STATUS_ARCHIVED: 'Archived',
            self.JOB_STATUS_ERROR_PATH: 'Error',
            self.JOB_STATUS_ERROR_DATA_SOURCE: 'Error',
        }

    def start(self):
        print("Starting...")
        db = Db("cgp_tags.sqlite", "jobs")
        self.db = db
        while True:
            sql = 'SELECT * FROM jobs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1'
            rows = db.get_all(sql)
            if rows:
                row = rows[0]
                self.preprocessJob(row)
            else:
                print(f"{YELLOW}{Utils.get_time()} No jobs for preprocessing{COLOR_END}")
            time.sleep(5)

    def secure_join(self, base_dir, *paths):
        # Join the base directory with the user-provided path
        target_path = os.path.join(base_dir, *paths)

        # Normalize the path to remove any '..' components
        normalized_path = os.path.normpath(target_path)

        # Ensure that the final path is within the base directory
        if os.path.commonpath([base_dir]) != os.path.commonpath([base_dir, normalized_path]):
            raise ValueError(f"Attempted Directory Traversal Detected: {[base_dir, normalized_path]}")

        return normalized_path

    def count_lines_in_file(self, file_path):
        with open(file_path, 'r') as file:
            return sum(1 for _ in file)

    def getUserId(self):
        return 1

    def validate(self, userId, job):
        # Check user-specific data path
        user_path = os.path.join(os.getcwd(), "user_data", str(userId))
        path = self.secure_join(user_path,job['url'])

        if not os.path.exists(path):
            print(f"{RED}Error: Path {path} not found. Aborting.{COLOR_END}")
            updateRow = {
                "id": job['id'],
                "status": self.JOB_STATUS_ERROR_PATH,
                "status_str": f"Path {path} not found",
            }
            #print(updateRow)
            self.db.save("jobs", updateRow)
            return

        # Collect list of files
        # TODO: Job specific data files
        # TODO: Handle Windows or Linux command lines
        extensions = ['.csv'] # , '.xslx' .txt
        files = self.list_files(path, extensions)

        if len(files) == 0:
            print(f"Path {path} empty. Aborting.")
            updateRow = {
                "id": job['id'],
                "status": self.JOB_STATUS_ERROR_EMPTY_PATH,
                "status_str": f"Path {path} empty",
            }
            self.db.save("jobs", updateRow)
            return
        return (path, files)

    def preprocessLocalFiles(self, job):
        pass


    def listHuggingFaceFiles(self, url):
        api_token = "TOKEN"
        api = HfApi(token=api_token)

        match = re.match(r"https://huggingface.co/([^/]+/[^/]+)", url)
        if not match:
            print("{RED}Invalid URL format: must be of the form 'https://huggingface.co/{model_or_dataset}. Aborting.'{COLOR_END}")
            return

        # Extract the model or dataset identifier
        repo_id = match.group(1)
        repo_id = "wenknow/reddit_dataset_209"
        print("repo_id", repo_id)

        # List the files in the repository
        files = api.list_repo_files(repo_id, repo_type="dataset")
        if False:
            # Gather detailed information about each file
            file_details = []
            for file_name in files:
                if True: #try:
                    # Download the file metadata to get more information
                    file_info = hf_hub_download(repo_id, file_name, token=api_token, cache_dir=None, force_filename=None, resume_download=False, force_download=False, etag_timeout=None, revision=None, local_dir=None, local_dir_use_symlinks=None)
                    # Since hf_hub_download primarily downloads files, you might need to check the cache or use API capabilities
                    # For sizes, consider accessing file system properties if directly downloading
                    file_size = os.path.getsize(file_info)  # Example method to get file size
                    file_details.append({
                        "file_name": file_name,
                        "file_size": file_size
                    })
                    print("{GREEN}file_info{COLOR_END}", file_info)
                else: #except Exception as e:
                    # Handle exceptions, such as missing metadata or failed downloads
                    print(f"Could not retrieve details for {file_name}: {e}")
                break

        return files

    def preprocessHuggingFace(self, job):
        print(f"{GREEN}HuggingFace JOB{COLOR_END}", job)
        url = "https://huggingface.co/datasets/wenknow/reddit_dataset_88"
        url = "https://huggingface.co/datasets/wenknow/reddit_dataset_209"
        url = "https://huggingface.co/datasets/fka/awesome-chatgpt-prompts"
        #url = "https://huggingface.co/gpt2"
        files = self.listHuggingFaceFiles(url)
        print("FILES", files)

    def preprocessJob(self, job):
        jobTypeId = Utils.get(job, 'job_type_id')
        print(f"{Utils.get_time()} Preprocessing job: {job} type: {jobTypeId}")

        if job['data_source_type_id'] == self.JOB_DATA_SOURCE_LOCAL:
            print(f"Checking for local files at path: {job['url']}...")
            userId = self.getUserId()
            (path, files) = self.validate(userId, job)
            if not files:
                return

            # Determine number of rows per file
            row_counts = {}
            for cur_file in files:
                fullRoute = os.path.join(path, cur_file)
                row_counts[cur_file] = self.count_lines_in_file(fullRoute)

                # Decide on chunk for the file
                task_type = 1
                if task_type == 1:
                    num_task_windows = int(row_counts[cur_file] / 1000) + 1
                updateJob = {
                    "id": job['id'],
                    "num_task_windows": num_task_windows,
                }
                for task_window_idx in range(num_task_windows):
                    taskRow = {
                        "status": 2,
                        "job_id": job['id'],
                        "task_window_index": task_window_idx,
                        "data_url": f"http://localhost:8001/user_data/1/contacts_20241105/{cur_file}",
                        "header_row_text": "id,convo",
                        "begin_row": 2,
                        "end_row": 5,
                        "data_type": 1,
                    }
                    print("taskRow", taskRow)
                    self.db.save("tasks", taskRow)

            print("row_counts", row_counts)
        elif job['data_source_type_id'] == self.JOB_DATA_SOURCE_HUGGING_FACE:
            self.preprocessHuggingFace(job)
        # Create tasks for each chunk
        if True:
            updateRow = {
                "id": job['id'],
                "status": 2,
            }
            print(updateRow)
            self.db.save("jobs", updateRow)

    def list_files(self, directory_path, extensions=None):
        try:
            # Get list of all entries in the directory
            entries = os.listdir(directory_path)
        except FileNotFoundError:
            print(f"The directory {directory_path} does not exist.")
            return None
        except PermissionError:
            print(f"Permission denied: unable to access {directory_path}.")
            return None

        # Filter entries to get files only
        files = [entry for entry in entries if os.path.isfile(os.path.join(directory_path, entry))]

        if extensions is not None:
            # Ensure extensions are in lowercase for case-insensitive comparison
            extensions = [ext.lower() for ext in extensions]
            # Filter files by extension
            files = [file for file in files if os.path.splitext(file)[1].lower() in extensions]

        return files


if __name__ == "__main__":
    pl = PreprocessorLib()
    pl.start()

