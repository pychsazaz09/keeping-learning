from storage.json_storage import JsonStorage

def get_storage()->JsonStorage:
    return JsonStorage("data/questions.json")