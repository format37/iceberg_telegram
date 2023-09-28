import json

data_path = 'data/'

with open(data_path+'prompts.json', 'r') as f:

    prompts = json.load(f)

# prompts is dict
# print each key
for key in prompts:
    print(key)
    # print(prompts[key])
