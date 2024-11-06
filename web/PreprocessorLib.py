import time
import os

from Utils import Utils
from Db import Db


class PreprocessorLib():
    def start(self):
        print("Starting...")
        db = Db("cgp_tags.sqlite", "jobs")
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
        # determine number of rows per file
        # Decide on chunk for the file
        # Create tasks for each chunk
        if False:
            updateRow = {
                "id": row['id'],
                "status": 2,
            }
            print(updateRow)
            db.save("jobs", updateRow)



if __name__ == "__main__":
    pl = PreprocessorLib()
    pl.start()

