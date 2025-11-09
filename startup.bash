#!/bin/bash
# Auto-setup script for application server
# Region: us-east-1

# Update system
yum update -y

# Install Python 3 and pip
yum install python3 python3-pip git -y

# Install required Python packages
pip3 install flask psutil requests

# Create app directory
mkdir -p /home/ec2-user/app
cd /home/ec2-user/app

# Get instance metadata
INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
REGION=$(ec2-metadata --availability-zone | cut -d ' ' -f 2 | sed 's/[a-z]$//')

# Create environment file
cat > /home/ec2-user/.env << EOF
export AWS_REGION=${REGION}
export INSTANCE_ID=${INSTANCE_ID}
export SERVER_PORT=5000
EOF

# Add to bashrc so it loads on login
echo "source /home/ec2-user/.env" >> /home/ec2-user/.bashrc

# Set ownership
chown -R ec2-user:ec2-user /home/ec2-user/app
chown ec2-user:ec2-user /home/ec2-user/.env

# Create completion marker
echo "Setup completed at $(date)" > /home/ec2-user/setup-complete.txt
echo "Region: ${REGION}" >> /home/ec2-user/setup-complete.txt
echo "Instance ID: ${INSTANCE_ID}" >> /home/ec2-user/setup-complete.txt

# Log completion
logger "User data script completed successfully"