#!/bin/bash
# Region: us-east-1

yum update -y
yum install python3 python3-pip git -y
pip3 install flask psutil requests
mkdir -p /home/ec2-user/app
cd /home/ec2-user/app

INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
REGION=$(ec2-metadata --availability-zone | cut -d ' ' -f 2 | sed 's/[a-z]$//')

cat > /home/ec2-user/.env << EOF
export AWS_REGION=${REGION}
export INSTANCE_ID=${INSTANCE_ID}
export SERVER_PORT=5000
EOF

echo "source /home/ec2-user/.env" >> /home/ec2-user/.bashrc

chown -R ec2-user:ec2-user /home/ec2-user/app
chown ec2-user:ec2-user /home/ec2-user/.env

echo "Setup completed at $(date)" > /home/ec2-user/setup-complete.txt
echo "Region: ${REGION}" >> /home/ec2-user/setup-complete.txt
echo "Instance ID: ${INSTANCE_ID}" >> /home/ec2-user/setup-complete.txt

logger "User data script completed successfully"