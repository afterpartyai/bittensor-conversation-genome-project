import time
import os

from Utils import Utils
from Db import Db


class PreprocessorLib():
    db = None

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

    def preprocessJob(self, job):
        print(f"Preprocessing job: {job}")
        # Access data source
        if job['data_source_type_id'] == 1:
            print(f"Checking for local files at path: {job['url']}...")
            user_id = 1
            user_path = os.path.join(os.getcwd(), "user_data", str(user_id))
            path = self.secure_join(user_path,job['url'])
            if not os.path.exists(path):
                print(f"Path {path} not found. Aborting.")
                updateRow = {
                    "id": job['id'],
                    "status": 99,
                    "status_str": f"Path {path} not found",
                }
                print(updateRow)
                #db.save("jobs", updateRow)
                return
        # Collect list of files
        extensions = ['.csv']
        files = self.list_files(path, extensions)
        # determine number of rows per file
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
                    "job_id": job['id'],
                    "task_window_index": task_window_idx,
                    "header_row_text": "",
                    "begin_row": 2,
                    "end_row": 5,
                    "data_type": 1,
                    "data_url": "",
                }
                self.db.save("tasks", taskRow)

        print("row_counts", row_counts)
        # Create tasks for each chunk
        if False:
            updateRow = {
                "id": row['id'],
                "status": 2,
            }
            print(updateRow)
            db.save("jobs", updateRow)

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

