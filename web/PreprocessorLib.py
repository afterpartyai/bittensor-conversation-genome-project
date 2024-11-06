import time
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
                print(f"Preprocessing job: {row}")
                updateRow = {
                    "id": row['id'],
                    "status": 2,
                }
                print(updateRow)
                db.save("jobs", updateRow)
            else:
                print(f"No jobs for preprocessing")
            time.sleep(5)


if __name__ == "__main__":
    pl = PreprocessorLib()
    pl.start()

