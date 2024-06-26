# stop container
sudo docker stop mrm_info_bot_test
# remove container
sudo docker rm mrm_info_bot_test
# run container
# -p 7403:8000 \
sudo docker run \
    --network host \
    --name mrm_info_bot_test \
    -e MRMSUPPORTBOT_AUTH_LOGIN="" \
    -e MRMSUPPORTBOT_AUTH_PASSWORD="" \
    -e OPENAI_API_KEY= \
    -e LANGCHAIN_TRACING_V2=true \
    -e LANGCHAIN_ENDPOINT=https://api.smith.langchain.com \
    -e LANGCHAIN_API_KEY= \
    -e LANGCHAIN_PROJECT="mrm_info" \
    -e MRMSUPPORTBOT_TOKEN="" \
    -v ./data:/server/data \
    mrm_info_bot