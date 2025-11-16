import requests

task_id = "1f975693-876d-457b-a649-393859e79bf3"
url = f"https://agents-course-unit4-scoring.hf.space/files/{task_id}"
response = requests.get(url)
print(response.text)





# url = "https://agents-course-unit4-scoring.hf.space/questions"
# response = requests.get(url)
# for _ in response.json():
#     print(_.get("question"))
#     print("Task ID: " + _.get("task_id"))
#     if _.get("file_name"):
#         print(f"file name: {_.get('file_name')}")
#     print("-"*100)