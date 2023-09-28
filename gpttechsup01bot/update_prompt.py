import json
import os
import logging

# init logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def load_default_config():
    conf_path = 'user_conf/'
    with open(conf_path+'config.json', 'r') as f:
        config = json.load(f)    
    return config


def read_config(path):
    with open(path, 'r') as f:
        config = json.load(f)
    logger.info('read_config: '+str(config))
    return config


def save_config(config, path):
    with open(path, 'w') as f:
        json.dump(config, f)


def main():
    # Read all json files in 'user_conf' folder
    folder = 'user_conf/'
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            conf = read_config(folder+filename)
            conf_default = load_default_config()
            # Update chat_gpt_prompt from default config
            conf['chat_gpt_prompt'] = conf_default['chat_gpt_prompt']
            # Update chat_gpt_init_prompt from default config
            conf['chat_gpt_init_prompt'] = conf_default['chat_gpt_init_prompt']
            # Save updated config
            save_config(conf, folder+filename)


if __name__ == '__main__':
    main()
