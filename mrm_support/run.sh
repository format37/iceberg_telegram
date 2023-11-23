# create folder for data
mkdir -p data
# stop container
sudo docker stop mrm_support_bot
# remove container
sudo docker rm mrm_support_bot
sudo docker run \
    -d \
    --restart always \
    -p 7404:7404 \
    --name mrm_support_bot \
    -e MRMSUPPORTBOT_AUTH_LOGIN="login" \
    -e MRMSUPPORTBOT_AUTH_PASSWORD="password" \
    -v $(pwd)/data:/server/data \
    -v $(pwd)/mnt/soft:/mnt/soft \
    mrm_support_bot
