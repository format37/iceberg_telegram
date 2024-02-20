# stop container
sudo docker stop mrm_info_bot
# remove container
sudo docker rm mrm_info_bot
# run container
sudo docker run \
    -d \
    --restart always \
    -p 7402:8000 \
    --name mrm_info_bot \
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