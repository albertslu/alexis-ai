#!/bin/bash

# SCP the Dockerfile and docker-compose.yml to EC2
scp -i "/Users/albertlu/Documents/AWS Instance KeyPair/coco-key.pem" /Users/albertlu/Documents/GitHub/ai-clone/ec2_dockerfile ec2-user@3.15.205.79:~/ai-clone/Dockerfile
scp -i "/Users/albertlu/Documents/AWS Instance KeyPair/coco-key.pem" /Users/albertlu/Documents/GitHub/ai-clone/ec2_docker_compose.yml ec2-user@3.15.205.79:~/ai-clone/docker-compose.yml

# Instructions for EC2
echo "Files transferred to EC2."
echo ""
echo "Run these commands on your EC2 instance:"
echo "cd ~/ai-clone"
echo "docker-compose down"
echo "docker-compose build"
echo "docker-compose up -d"
echo "docker-compose logs -f"
