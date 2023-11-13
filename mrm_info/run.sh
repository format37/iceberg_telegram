# sudo docker run -d --restart always --name mrm_info_bot -p 7402:7402 mrm_info_bot
# sudo docker run -p 7402:7402  mrm_info_bot
# stop container
sudo docker stop mrm_info_bot
# remove container
sudo docker rm mrm_info_bot
sudo docker run \
    -d \
    --restart always \
    -p 7402:7402 \
    --name mrm_info_bot \
    -e MRMSUPPORTBOT_AUTH_LOGIN="login" \
    -e MRMSUPPORTBOT_AUTH_PASSWORD="password" \
    mrm_info_bot