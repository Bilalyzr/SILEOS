import os

files_to_search = [
    (r"D:\GitDesk\Sasha Inifinity\Sasha_lms\backend\app\routers\quizzes.py", ["submit", "start", "attempts-count"]),
    (r"D:\GitDesk\Sasha Inifinity\Sasha_lms\backend\app\routers\assignments.py", ["submit", "assignments"])
]

for file_path, keywords in files_to_search:
    if os.path.exists(file_path):
        print(f"=== Searching {os.path.basename(file_path)} ===")
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if "@router." in line or any(k in line for k in keywords):
                    if "@router." in line:
                        print(f"{i}: {line.strip()}")
