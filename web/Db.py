import os
import sqlite3
import json

from Utils import Utils
from models.conversation_record import ConversationRecord


class Db:
    source_type = 2  # Non-CGP
    db_name = None
    table_name = None
    sql_create_results = """CREATE TABLE IF NOT EXISTS cgp_results (
	"id"	INTEGER UNIQUE,
	"status"	INTEGER DEFAULT 1,
	"batch_num"	INTEGER,
	"c_guid"	TEXT,
	"convo_window_index"	INTEGER DEFAULT 1,
	"source_type"	INTEGER DEFAULT 2,
	"mode"	TEXT,
	"hotkey"	TEXT,
	"coldkey"	TEXT,
	"uid"	INTEGER,
	"llm_type"	TEXT,
	"model"	TEXT,
	"tags"	JSON,
	"marker_id"	INTEGER,
	"json"	JSON,
	"created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"cgp_version"	TEXT
	"updated_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"updated_by"	INTEGER,
	"created_by"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
)"""

    def __init__(self, db_name, table_name):
        self.db_name = db_name
        self.table_name = table_name

    def get_cursor(self):
        db_name = os.path.join(os.path.dirname(__file__), 'conversations.sqlite')
        conn = sqlite3.connect(db_name)
        conn.row_factory = Db.dict_factory
        cursor = conn.cursor()

        return cursor

    def insert_into_table(self, c_guid, content):
        today = Utils.get_time("%Y.%m.%d")
        db_name = f"{self.db_name}_{today}.sqlite"
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(self.sql_create_results)
        updateRow = {
            "c_guid": c_guid,
            "mode": Utils.get(content, "mode"),
            "model": Utils.get(content, "model"),
            "llm_type": Utils.get(content, "llm_type"),
            "convo_window_index": Utils.get(content, "convo_window_index"),
            "marker_id": Utils.get(content, "marker_id"),
            "source_type": self.source_type,
            "hotkey": Utils.get(content, "hotkey"),
            "coldkey": Utils.get(content, "coldkey"),
            "batch_num": Utils.get(content, "batch_num"),
            "tags": Utils.get(content, "tags"),
            "cgp_version": Utils.get(content, "cgp_version"),
            "json": json.dumps(content),
        }
        fields = []
        questions = []
        values = []
        for field, val in updateRow.items():
            fields.append(field)
            questions.append("?")
            values.append(val)
        fields_str = ",".join(fields)
        questions_str = ",".join(questions)
        cursor.execute(f"INSERT INTO cgp_results ({fields_str}) VALUES ({questions_str})", (values))
        conn.commit()
        conn.close()

    def get_random_conversation(self) -> ConversationRecord:
        cursor = self.get_cursor()
        sql = 'SELECT * FROM conversations ORDER BY RANDOM() LIMIT 1'
        cursor.execute(sql)
        rows = cursor.fetchall()
        if rows and len(rows) == 1:
            return ConversationRecord(**rows[0])
        else:
            return None

    def get_conversation(self, guid):
        print(guid)
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM conversations WHERE guid = ?", (guid,))
        rows = cursor.fetchall()
        if rows and len(rows) == 1:
            return ConversationRecord(**rows[0])
        else:
            return None

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            if col[0] == "json":
                try:
                    d["data"] = json.loads(row[idx])
                except:
                    d["data"] = json.loads("{}")
            else:
                d[col[0]] = row[idx]
        return d
