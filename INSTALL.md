# Installation Guide

This document provides comprehensive instructions for installing and configuring the DR Setup Guide.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Operating System

- Linux (Ubuntu 20.04 LTS or later, CentOS 7+, Amazon Linux 2)
- macOS (10.15 or later)
- Windows 10/11 (with WSL2 or Git Bash)

### Software Requirements

- **Python**: 3.8 or higher
  ```bash
  python3 --version  # Should show Python 3.8+
  ```
- **pip**: 21.0 or higher
  ```bash
  pip3 --version  # Should show pip 21.0+
  ```
- **Git**: 2.25 or higher
  ```bash
  git --version
  ```

### CLI Tools Required

- **Confluent CLI**: For Confluent Cloud operations
  ```bash
  confluent version
  ```
- **AWS CLI v2**: For AWS operations
  ```bash
  aws --version
  ```
- **kubectl**: For Kubernetes operations
  ```bash
  kubectl version --client
  ```
- **aws-iam-authenticator**: For EKS authentication
  ```bash
  aws-iam-authenticator version
  ```

### AWS Permissions

Required IAM permissions for your AWS user/role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:UpdateSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:*"
    }
  ]
}
```

### Confluent Cloud Permissions

- Environment Admin role
- Cluster Admin role for both production and DR clusters
- Schema Registry Admin access

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ssenapathy-wam/dr-setup-guide.git
cd dr-setup-guide
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Package

```bash
# Install with dependencies
pip install -e .

# Or with development tools
pip install -e ".[dev]"
```

### 4. Setup Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env  # or your preferred editor
```

### 5. Verify Installation

```bash
# Check Python packages
pip check

# Run basic test
python -c "from command_executor import CommandExecutor; print('✓ Installation successful')"
```

## Detailed Installation

### Step 1: Install System Dependencies (Linux)

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev
sudo apt-get install -y git curl wget
```

#### CentOS/RHEL

```bash
sudo yum install -y python3 python3-pip python3-devel
sudo yum install -y git curl wget
```

#### Amazon Linux 2

```bash
sudo yum install -y python3 python3-pip python3-devel
sudo yum install -y git curl wget
```

### Step 2: Install AWS CLI v2

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### Step 3: Install kubectl

```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# macOS
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Verify
kubectl version --client
```

### Step 4: Install aws-iam-authenticator

```bash
# Linux
curl -o aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/1.27.1/2023-06-14/bin/linux/amd64/aws-iam-authenticator
chmod +x aws-iam-authenticator
sudo mv aws-iam-authenticator /usr/local/bin/

# macOS
curl -o aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/1.27.1/2023-06-14/bin/darwin/amd64/aws-iam-authenticator
chmod +x aws-iam-authenticator
sudo mv aws-iam-authenticator /usr/local/bin/

# Verify
aws-iam-authenticator version
```

### Step 5: Install Confluent CLI

```bash
# Download latest version
curl -sL --http1.1 https://cnfl.io/cli_v2_linux | tar xzf -

# Add to PATH
export PATH=$PATH:./bin
# Or permanently add to ~/.bashrc or ~/.zshrc

# Verify
confluent version
```

### Step 6: Clone and Setup Project

```bash
git clone https://github.com/ssenapathy-wam/dr-setup-guide.git
cd dr-setup-guide

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

## Configuration

### 1. Create .env File

```bash
cp .env.example .env
```

### 2. Edit Configuration

```bash
nano .env  # or your preferred editor
```

### 3. Key Configuration Items

#### Confluent Cloud

```ini
# Production Environment
CONFLUENT_PROD_ENV_ID=env-xxxxx
CONFLUENT_PROD_CLUSTER_ID=lkc-xxxxx
CONFLUENT_PROD_API_KEY=your_api_key
CONFLUENT_PROD_API_SECRET=your_api_secret
CONFLUENT_PROD_BOOTSTRAP=pkc-prod.your-region.provider.confluent.cloud:9092

# DR Environment
CONFLUENT_DR_ENV_ID=env-xxxxx
CONFLUENT_DR_CLUSTER_ID=lkc-xxxxx
CONFLUENT_DR_API_KEY=your_api_key
CONFLUENT_DR_API_SECRET=your_api_secret
CONFLUENT_DR_BOOTSTRAP=pkc-dr.your-region.provider.confluent.cloud:9092
```

#### AWS Configuration

```ini
AWS_REGION=us-west-2
AWS_PROFILE=default
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
EKS_CLUSTER_NAME=your-eks-cluster-name
```

#### Kubernetes Configuration

```ini
K8S_NAMESPACE=your-namespace
K8S_SECRET_NAME=kafka-credentials-secret
K8S_CONNECTOR_LABEL=app=connectors
```

### 4. Validate Configuration

```bash
# Test Confluent credentials
confluent auth login --save

# Test AWS credentials
aws sts get-caller-identity

# Test Kubernetes access
kubectl cluster-info
```

## Verification

### 1. Verify Python Installation

```bash
python3 --version
pip list | grep -E "confluent|boto3|kubernetes"
```

### 2. Verify CLI Tools

```bash
# Check all required tools
confluent version
aws --version
kubectl version --client
aws-iam-authenticator version
```

### 3. Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run test suite
make test

# Run with coverage
make test-cov
```

### 4. Test Connectivity

```bash
# Test Confluent
confluent environment list

# Test AWS
aws eks describe-cluster --name $EKS_CLUSTER_NAME --region $AWS_REGION

# Test Kubernetes
kubectl get nodes
```

### 5. Run Dry Run

```bash
make run-dry-run
```

## Troubleshooting

### Python Version Issues

```bash
# Verify Python 3.8+
python3 --version

# If using multiple Python versions
python3.10 -m venv venv
```

### Virtual Environment Issues

```bash
# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### Dependency Conflicts

```bash
# Check for conflicts
pip check

# Update pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Reinstall from scratch
pip install -e . --force-reinstall
```

### AWS Credential Issues

```bash
# Verify AWS configuration
aws configure list

# Check credentials file
cat ~/.aws/credentials

# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2
```

### Kubernetes Connection Issues

```bash
# Update kubeconfig
aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $AWS_REGION

# Verify connection
kubectl cluster-info
kubectl get nodes

# Check current context
kubectl config current-context
```

### Confluent CLI Issues

```bash
# Login again
confluent auth login --save

# Check environment
confluent environment list

# Set environment
confluent environment use <env-id>
```

### Missing Dependencies

```bash
# Install missing CLI tools
# For Ubuntu
sudo apt-get install -y python3-dev build-essential

# Reinstall Python dependencies
pip install --upgrade -e ".[dev]"
```

## Next Steps

After successful installation:

1. Read [README.md](README.md) for project overview
2. Check [DR_SETUP_COMPLETE_GUIDE.md](DR_SETUP_COMPLETE_GUIDE.md) for detailed setup instructions
3. Review [CONTRIBUTING.md](CONTRIBUTING.md) if you plan to contribute
4. Run `make run-dry-run` to test the setup process

## Support

If you encounter issues:

1. Check this troubleshooting section
2. Review logs in `logs/` directory
3. Check [GitHub Issues](https://github.com/ssenapathy-wam/dr-setup-guide/issues)
4. Refer to official documentation for Confluent, AWS, and Kubernetes

## Version Information

- **Project Version**: 1.0.0
- **Python Support**: 3.8 - 3.12
- **Last Updated**: 2024
