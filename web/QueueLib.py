
def download_data_sources():
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

def get_queue_item():
    priorities = [1,2,3]
    item = None
    for priority in priorities:
        sql = "UPDATE queue_items SET "
        # Search for p1 items, and so on
        if found:
            break
    if item:
        # Reserve item
        pass

if __name__ == "__main__":
    print("Run")
