# stop container
sudo docker stop mrm_info_bot_test
# remove container
sudo docker rm mrm_info_bot_test
# run container
sudo docker run \
    -d \
    --restart always \
    -p 7403:7403 \
    --name mrm_info_bot_test \
    -e MRMSUPPORTBOT_AUTH_LOGIN="login" \
    -e MRMSUPPORTBOT_AUTH_PASSWORD="password" \
    mrm_info_bot
