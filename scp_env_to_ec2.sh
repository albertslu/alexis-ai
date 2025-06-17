#!/bin/bash

# SCP the .env.production file to EC2
scp -i "/Users/albertlu/Documents/AWS Instance KeyPair/coco-key.pem" /Users/albertlu/Documents/GitHub/ai-clone/.env.production ec2-user@3.15.205.79:~/ai-clone/.env.production

echo "Environment file transferred to EC2."
