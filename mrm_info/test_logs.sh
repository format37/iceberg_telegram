# get id of running container with image name
# container_id=$(sudo docker ps | grep mrm_info_bot | awk '{print $1}')
# echo "container id: $container_id"
# get logs
# sudo docker logs -f $container_id
sudo docker logs -f mrm_info_bot_test
# connect to container
# sudo docker exec -it $container_id /bin/bash
