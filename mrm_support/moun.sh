echo "Mounting /mnt/soft for apk"
sudo mount -t cifs //10.2.4.88/Distrib/web_published /mnt/soft -o username=1csystem,domain=ICECORP,vers=3.0
echo "Mounting /mnt/photos for photos"
sudo mount -t cifs //10.2.4.164/data/photos /mnt/photos -o username=1csystem,domain=ICECORP,vers=3.0
echo "Done"