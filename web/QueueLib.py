
class QueueLib:
    def download_data_sources(self):
        # Find all rows that have a data source not available
        # status = 4 group by type, url ORDER BY count DESC limit 1
        if type == HUGGING_FACE:
            # Use HF library
            pass
        elif type == S3:
            # Use httpx
            pass
        elif type == url:
            # Use httpx
            pass

    def get_queue_item(self):
        priorities = [1,2,3]
        item = None
        found = False
        for priority in priorities:
            sql = "UPDATE queue_items SET "
            # Search for p1 items, and so on
            if found:
                break
        if item:
            # Reserve item
            pass
        item = {"type":"alsdj"}
        return item

if __name__ == "__main__":
    ql = QueueLib()
    print("Run")
    action = "get_queue"

    if action == "get_queue":
        item = ql.get_queue_item()
        print("ITEM", item)


