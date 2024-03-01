# sudo docker run -d --restart always --name mrm_info_bot -p 7402:7402 mrm_info_bot
# sudo docker run -p 7402:7402  mrm_info_bot
# stop container
sudo docker stop mrm_info_proxy
# remove container
sudo docker rm mrm_info_proxy
sudo docker run \
    -d \
    --restart always \
    -p 7403:7403 \
    --name mrm_info_proxy \
    -e MRMSUPPORTBOT_AUTH_LOGIN="login" \
    -e MRMSUPPORTBOT_AUTH_PASSWORD="password" \
    -e MRMSUPPORTBOT_TOKEN="token" \
    -v /etc/letsencrypt/live/yourdomain.com/fullchain.pem:/cert/webhook_cert.pem \
    -v /etc/letsencrypt/live/yourdomain.com/privkey.pem:/cert/webhook_pkey.pem \
    -v /mnt/soft:/mnt/soft
    mrm_info_proxy
