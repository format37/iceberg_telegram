###
# This is a flask server that will be used to remove files on a proposed folder
###

from flask import Flask, request, jsonify
import os
import logging
import logging.handlers
import shutil

app = Flask(__name__)

# Init logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting")


@app.route('/test', methods=['GET'])
def test():
    return 'ok'


@app.route('/delete', methods=['GET'])
def delete_folder():

    # Get parameters
    key = request.args.get('key')
    if key != os.environ.get('KEY'):
        result = "Invalid key: "+str(key)
        logger.error(result)
        return result
        
    folder = request.args.get('folder')
    logger.info("Deleting folder: " + folder)

    # Remove folder
    try:
        # if it is a folder:
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        # if it is a file:
        else:
            os.remove(folder)
        logger.info("Folder deleted")
        return 'ok'
    except Exception as e:
        result = "Error deleting folder: " + str(e)
        logger.error(result)
        return result


def main():
    # Init logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting")

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    # Start server
    app.run(host=host, port=port)


if __name__ == '__main__':
    main()
