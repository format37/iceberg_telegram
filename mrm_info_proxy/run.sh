# sudo docker run -d --restart always --name mrm_info_bot -p 7402:7402 mrm_info_bot
# sudo docker run -p 7402:7402  mrm_info_bot
# stop container
sudo docker stop mrm_info_proxy
# remove container
sudo docker rm mrm_info_proxy
sudo docker run \
    -d \
    --restart always \
    -p 7402:7402 \
    --name mrm_info_proxy \
    -e MRMSUPPORTBOT_AUTH_LOGIN="login" \
    -e MRMSUPPORTBOT_AUTH_PASSWORD="password" \
    -e MRMSUPPORTBOT_TOKEN="token" \
    mrm_info_proxy
