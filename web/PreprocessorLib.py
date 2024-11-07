import time
import os

from Utils import Utils
from Db import Db


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
            print(".")
            sql = 'SELECT * FROM jobs WHERE status = 1 ORDER BY updated_at DESC LIMIT 1'
            rows = db.get_all(sql)
            if rows:
                row = rows[0]
                self.preprocessJob(row)
            else:
                print(f"No jobs for preprocessing")
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

    def preprocessJob(self, job):
        jobTypeId = Utils.get(job, 'job_type_id')
        print(f"Preprocessing job: {job} type: {jobTypeId}")

        if job['data_source_type_id'] == self.JOB_DATA_SOURCE_LOCAL:
            print(f"Checking for local files at path: {job['url']}...")
            userId = getUserId()

            # Check user-specific data path
            user_path = os.path.join(os.getcwd(), "user_data", str(user_id))
            path = self.secure_join(user_path,job['url'])

            if not os.path.exists(path):
                print(f"Path {path} not found. Aborting.")
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
        # Create tasks for each chunk
        if True:
            updateRow = {
                "id": job['id'],
                "status": 2,
            }
            print(updateRow)
            self.db.save("jobs", updateRow)

    def list_files(self, directory_path, extensions=None):
        """
        List files in the given directory with specified extensions.

        :param directory_path: Path to the directory to scan.
        :param extensions: List of file extensions to filter by, or None to return all files.
        :return: List of matching file names.
        """
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

