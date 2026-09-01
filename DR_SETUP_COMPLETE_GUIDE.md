# Complete Disaster Recovery (DR) Setup Guide for Confluent Cloud & Kafka Connect

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Confluent Cloud DR Cluster Setup](#phase-1-confluent-cloud-dr-cluster-setup)
4. [Phase 2: Creating Cluster Link (Prod to DR)](#phase-2-creating-cluster-link-prod-to-dr)
5. [Phase 3: Mirroring Topics](#phase-3-mirroring-topics)
6. [Phase 4: Schema Registry Synchronization](#phase-4-schema-registry-synchronization)
7. [Phase 5: Topic Promotion](#phase-5-topic-promotion)
8. [Phase 6: Kafka Connect Setup on EKS](#phase-6-kafka-connect-setup-on-eks)
9. [Phase 7: Secret Management & Connector Updates](#phase-7-secret-management--connector-updates)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide documents the complete process for setting up a Disaster Recovery (DR) environment using Confluent Cloud. The process involves:

- **Confluent Cloud Setup**: Creating a DR cluster and establishing a cluster link from production
- **Data Replication**: Mirroring critical topics to the DR cluster
- **Schema Management**: Syncing schemas using Schema Registry exporters
- **Topic Readiness**: Promoting mirrored topics to make them writable
- **Application Failover**: Updating Kafka Connect deployments on AWS EKS to point to mirrored topics

**Timeline**: Based on command history (Aug 10 - Aug 31, 2026), this process takes approximately 3 weeks to complete, including setup, testing, and secret rotation.

---

## Prerequisites

### Required Accounts & Access
- **Confluent Cloud Account**: Access to both production and DR environments
- **AWS Account**: EKS cluster access with appropriate IAM permissions
- **Kubernetes**: `kubectl` configured and authenticated to EKS cluster
- **Confluent CLI**: Installed locally (`confluent` command available)
- **AWS CLI**: Configured with appropriate AWS profiles

### Required Credentials
- Confluent Cloud API credentials
- AWS API credentials (configured in `~/.aws/credentials`)
- Kubernetes service account credentials
- Kafka broker credentials (API keys, SASL credentials)
- Schema Registry credentials

### Cluster Information to Gather
- **Production Kafka Cluster ID**: (e.g., `lkc-m2qgx`)
- **DR Kafka Cluster ID**: (e.g., `lkc-xqrk0kz`)
- **Production Environment ID**: (e.g., `env-xrwzz`)
- **EKS Cluster Name**: (e.g., `es-wt-eks-cluster-nonprod`)
- **AWS Region**: (e.g., `us-west-2`)

---

## Phase 1: Confluent Cloud DR Cluster Setup

### Step 1.1: Authenticate to Confluent Cloud

```bash
confluent login --no-browser
```

**What this does**: 
- Initiates authentication to Confluent Cloud
- `--no-browser` flag allows authentication in terminal-only environments
- Credentials are stored locally for subsequent commands

### Step 1.2: List Available Environments

```bash
confluent environment list
```

**What this does**: 
- Displays all available Confluent Cloud environments
- Helps identify the correct environment to work with

**Sample Output**:
```
ID           | Name
env-xrwzz    | Production
env-dr       | Disaster Recovery
```

### Step 1.3: Select the DR Environment

```bash
confluent environment use env-xrwzz
```

**What this does**: 
- Sets the current working environment to the DR environment
- All subsequent commands operate within this environment context
- Replace `env-xrwzz` with your actual DR environment ID

**Note**: This environment should already be pre-created in Confluent Cloud. If not, create it through the Confluent Cloud UI before proceeding.

### Step 1.4: Verify Network Configuration

```bash
confluent network list
```

**What this does**: 
- Lists all networks configured in the environment
- Verifies network connectivity setup between prod and DR
- Ensures proper VPC/Private Link configuration

### Step 1.5: Create or Identify DR Kafka Cluster

```bash
confluent kafka cluster list
```

**What this does**: 
- Lists all Kafka clusters in the current environment
- Identifies the DR cluster ID (e.g., `lkc-xqrk0kz`)
- Confirms the cluster is running and accessible

**Expected Output**:
```
ID           | Name              | Type    | Byok   | Availability
lkc-xqrk0kz  | dr-cluster        | DEDICATED | false | multi-zone
```

> **Important**: The DR cluster should be created manually through the Confluent Cloud console or via CLI before this step. Match the production cluster's specifications (broker count, storage, performance tier).

---

## Phase 2: Creating Cluster Link (Prod to DR)

### What is a Cluster Link?

A **Cluster Link** is a secure, unidirectional connection between two Kafka clusters that enables:
- Topic mirroring
- Schema replication
- Automatic data synchronization
- Disaster recovery failover capability

### Step 2.1: List Existing Cluster Links

```bash
confluent kafka link list --cluster lkc-pgkwmjy
```

```bash
confluent kafka link list --cluster lkc-xqrk0kz
```

**What this does**: 
- Lists all existing cluster links for each cluster
- `--cluster` flag specifies which cluster to query
- Helps identify if a link already exists

**Why run on both clusters?**: 
- First command checks production cluster links
- Second command checks DR cluster links
- Ensures no duplicate links are created

### Step 2.2: Create Cluster Link from Production to DR

```bash
confluent kafka link create cl-prod-to-dr \
  --cluster lkc-xqrk0kz \
  --source-cluster-id lkc-m2qgx \
  --config-file config_prod.txt
```

**What this does**: 
- Creates a unidirectional cluster link named `cl-prod-to-dr`
- `--cluster lkc-xqrk0kz`: Specifies the **destination** cluster (DR)
- `--source-cluster-id lkc-m2qgx`: Specifies the **source** cluster (Production)
- `--config-file config_prod.txt`: Applies configuration settings

**Expected Structure of config_prod.txt**:
```
# Production Cluster Link Configuration
bootstrap.servers=pkc-prod.region.provider.confluent.cloud:9092
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
sasl.username=<PROD_API_KEY>
sasl.password=<PROD_API_SECRET>
```

**Replace with your values**:
- `<PROD_API_KEY>`: Production cluster API key
- `<PROD_API_SECRET>`: Production cluster API secret

### Step 2.3: Verify Cluster Link Creation

```bash
confluent kafka link list --cluster lkc-xqrk0kz
```

**What this does**: 
- Confirms the cluster link was created successfully
- Shows link status (should be READY or INITIATED)
- Displays link configuration details

**Expected Output**:
```
Name              | Source Cluster | Destination Cluster | State   | Error
cl-prod-to-dr     | lkc-m2qgx      | lkc-xqrk0kz        | READY   | 
```

---

## Phase 3: Mirroring Topics

### What is Topic Mirroring?

Topic mirroring creates an automated, continuous copy of topics from source to destination cluster. Mirrored topics:
- Replicate all data (messages, offsets, key/value data)
- Are initially **read-only** (unless promoted)
- Maintain source partition count and configuration
- Can be promoted to become writable

### Step 3.1: Create Mirror Topics

Mirror topics are created one at a time. The following command creates a mirror of a topic using the cluster link:

```bash
confluent kafka mirror create dap.portfolio.compact.portfolio-master-for-analytics.avro \
  --link cl-prod-to-dr \
  --cluster lkc-xqrk0kz
```

**What this does**: 
- Creates a mirror of the source topic on the DR cluster
- `--link cl-prod-to-dr`: Uses the cluster link created in Phase 2
- `--cluster lkc-xqrk0kz`: Specifies the destination (DR) cluster
- Topic name remains the same across clusters
- Data starts replicating immediately

**Topic Naming**: 
- Mirror topics retain the same name as source topics
- Example: `dap.portfolio.compact.portfolio-master-for-analytics.avro`

### Step 3.2: Verify Mirror Topic Creation

```bash
confluent kafka topic describe dev.gdr.analytics.compact.bmk-analytic.avro \
  --cluster lkc-xqrk0kz
```

```bash
confluent kafka topic describe dap.portfolio.compact.portfolio-master-for-analytics.avro \
  --cluster lkc-xqrk0kz
```

**What this does**: 
- Shows detailed information about mirrored topics on DR cluster
- Verifies partition count, replication factor, and configuration
- Confirms mirror status (should show as read-only initially)

**Expected Output**:
```
Topic Name: dap.portfolio.compact.portfolio-master-for-analytics.avro
Partitions: 8
Replication Factor: 3
Configs: 
  - min.insync.replicas: 2
  - cleanup.policy: compact
  - retention.ms: 604800000
```

### Step 3.3: Repeat for All Critical Topics

For each topic that needs to be mirrored:

```bash
confluent kafka mirror create <TOPIC_NAME> \
  --link cl-prod-to-dr \
  --cluster lkc-xqrk0kz
```

**Topics to Mirror** (identify from production):
- All application-critical topics
- Topics with historical data requirements
- Topics used by critical connectors
- Topics with analytics dependencies

**Monitoring Replication**: 
- Initial replication can take time depending on topic size
- Monitor replication lag through Confluent Cloud UI
- Replication typically completes within minutes to hours

---

## Phase 4: Schema Registry Synchronization

### What is Schema Registry Exporter?

A Schema Registry Exporter:
- Continuously syncs schemas from production to DR
- Maintains schema versioning and compatibility
- Handles schema evolution
- Works with AVRO, Protobuf, and JSON Schema formats

### Step 4.1: Login to Confluent Cloud

```bash
confluent login --no-browser
```

### Step 4.2: Select DR Environment

```bash
confluent environment use env-xrwzz
```

### Step 4.3: Create Schema Registry Exporter

```bash
confluent schema-registry exporter create \
  prod-to-dr-schema-exporter \
  --context-type CUSTOM \
  --context-name prod \
  --subjects ":*:" \
  --config config_schema.txt
```

**What this does**: 
- Creates an exporter named `prod-to-dr-schema-exporter`
- `--context-type CUSTOM`: Specifies custom schema context
- `--context-name prod`: Schema context name in production
- `--subjects ":*:"`: Exports ALL schemas (wildcard pattern)
- `--config config_schema.txt`: Configuration file with connection details

**Expected Structure of config_schema.txt**:
```
# Source (Production) Schema Registry Configuration
bootstrap.servers=pkc-prod.region.provider.confluent.cloud:9092
schema.registry.url=https://psrc-prod.region.provider.confluent.cloud
schema.registry.basic.auth.user.info=<SR_API_KEY>:<SR_API_SECRET>
schema.registry.client.namespace.id=<NAMESPACE_ID>

# Destination (DR) Schema Registry Configuration
destination.schema.registry.url=https://psrc-dr.region.provider.confluent.cloud
destination.schema.registry.basic.auth.user.info=<DR_SR_API_KEY>:<DR_SR_API_SECRET>
```

**Configuration Parameters**:
- `<SR_API_KEY>`: Production Schema Registry API key
- `<SR_API_SECRET>`: Production Schema Registry API secret
- `<DR_SR_API_KEY>`: DR Schema Registry API key
- `<DR_SR_API_SECRET>`: DR Schema Registry API secret

### Step 4.4: List Schema Registry Exporters

```bash
confluent schema-registry exporter list
```

**What this does**: 
- Shows all configured exporters
- Displays exporter names and status
- Helps verify exporter was created

**Expected Output**:
```
Name                             | Status | Subjects
prod-to-dr-schema-exporter       | RUNNING | 5/5 exported
```

### Step 4.5: Describe Exporter Status

```bash
confluent schema-registry exporter status describe prod-to-dr-schema-exporter
```

**What this does**: 
- Shows detailed status of the exporter
- Displays number of schemas exported
- Shows any export errors or issues
- Indicates last sync timestamp

### Step 4.6: View Exporter Details

```bash
confluent schema-registry exporter describe prod-to-dr-schema-exporter
```

**What this does**: 
- Displays complete exporter configuration
- Shows source and destination schema registries
- Lists exported subjects
- Useful for troubleshooting and verification

---

## Phase 5: Topic Promotion

### What is Topic Promotion?

By default, mirrored topics are **read-only** to prevent accidental writes. Topic promotion:
- Converts read-only mirror topics to **writable** topics
- Stops replication from source
- Allows applications to write to the topic
- Is a **one-way operation** (cannot be reversed)

### When to Promote?

- When failover to DR is initiated
- After verifying replication is complete
- Before redirecting applications to DR
- Only after confirming production cluster is down or unreachable

### Step 5.1: Promote Mirror Topic

```bash
confluent kafka mirror promote dap.portfolio.compact.portfolio-master-for-analytics.avro \
  --link cl-prod-to-dr \
  --cluster lkc-xqrk0kz
```

**What this does**: 
- Promotes a mirror topic to make it writable
- `--link cl-prod-to-dr`: Specifies the cluster link
- `--cluster lkc-xqrk0kz`: Specifies the DR cluster
- Topic becomes read-write capable
- Replication stops for this topic

**Important Considerations**:
- This is **irreversible** - once promoted, cannot re-enable mirroring
- Perform only when initiating actual failover
- Verify all data has been replicated before promotion
- Coordinate with application teams before promoting

### Step 5.2: Verify Promotion Status

After promotion, verify the topic status:

```bash
confluent kafka topic describe dap.portfolio.compact.portfolio-master-for-analytics.avro \
  --cluster lkc-xqrk0kz
```

**Expected Changes**:
- Topic should now show as read-write (not read-only)
- Replication status should show stopped
- Mirror status should indicate promotion complete

### Step 5.3: Repeat for All Critical Topics

Promote all topics that applications need to write to:

```bash
confluent kafka mirror promote <TOPIC_NAME> \
  --link cl-prod-to-dr \
  --cluster lkc-xqrk0kz
```

---

## Phase 6: Kafka Connect Setup on EKS

### Overview

Kafka Connect is deployed on an AWS EKS cluster. In this phase, we:
1. Configure AWS credentials
2. Access the EKS cluster
3. Identify Kafka Connect connectors
4. Create new connectors pointing to DR topics
5. Update secrets for DR authentication

### Step 6.1: Set AWS Profile

```bash
export AWS_PROFILE=DEVCICD
```

**What this does**: 
- Sets the AWS profile for all subsequent AWS CLI commands
- `DEVCICD` is the profile configured in `~/.aws/credentials`
- Ensures correct AWS account access

**AWS Credentials File Location**: `~/.aws/credentials`

**Expected Format**:
```
[DEVCICD]
aws_access_key_id=AKIA...
aws_secret_access_key=...
region=us-west-2
```

### Step 6.2: Update EKS Cluster Configuration

```bash
aws eks update-kubeconfig \
  --region us-west-2 \
  --name es-wt-eks-cluster-nonprod
```

**What this does**: 
- Downloads EKS cluster configuration
- Updates `~/.kube/config` with cluster credentials
- Enables `kubectl` commands to access the cluster
- `--region us-west-2`: AWS region where EKS cluster runs
- `--name es-wt-eks-cluster-nonprod`: EKS cluster name

**Result**: 
- `kubectl` is now configured to communicate with the EKS cluster
- All subsequent `kubectl` commands target this cluster

### Step 6.3: Verify Cluster Access

```bash
kubectl get nodes
```

**What this does**: 
- Lists all nodes in the EKS cluster
- Confirms successful authentication
- Shows node status and readiness

**Expected Output**:
```
NAME                                            STATUS   ROLES    AGE
ip-10-0-1-150.us-west-2.compute.internal        Ready    <none>   45d
ip-10-0-2-200.us-west-2.compute.internal        Ready    <none>   45d
```

### Step 6.4: List All Pods in Cluster

```bash
kubectl get pods --all-namespaces
```

**What this does**: 
- Shows all running pods across all namespaces
- Helps locate Kafka Connect deployment pods
- Displays pod status and readiness

**Searching for Kafka Connect Pods**:
- Look for pods with names containing "connectors" or "connect"
- Note the namespace where they're deployed (often `operator-uat` or similar)

### Step 6.5: Get Kafka Connect Pods with Image Information

```bash
kubectl get pods -l app=connectors -n operator-uat \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
```

**What this does**: 
- Lists pods with label `app=connectors` in namespace `operator-uat`
- Shows pod name and container image
- `-l app=connectors`: Label selector to filter pods
- `-n operator-uat`: Specifies the namespace
- `-o jsonpath`: Formats output to show specific fields

**Expected Output**:
```
connectors-0                    confluentinc/cp-kafka-connect:7.3.0
connectors-1                    confluentinc/cp-kafka-connect:7.3.0
connectors-2                    confluentinc/cp-kafka-connect:7.3.0
```

---

## Phase 7: Secret Management & Connector Updates

### Overview

Kafka Connect pods authenticate to Kafka brokers using credentials stored in Kubernetes Secrets. To work with DR cluster, these secrets must be updated with DR broker credentials.

### Step 7.1: View Current Secrets

```bash
kubectl get secret secret-kafka -n operator-uat -o yaml
```

**What this does**: 
- Displays the complete YAML definition of the secret
- Shows encoded credentials and configuration
- `-o yaml`: Outputs in YAML format for easy review

**Expected Structure**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: secret-kafka
  namespace: operator-uat
type: Opaque
data:
  username: <base64-encoded-username>
  password: <base64-encoded-password>
  sasl.username: <base64-encoded-username>
  sasl.password: <base64-encoded-password>
```

### Step 7.2: Backup Existing Secret

```bash
kubectl get secret secret-kafka -n operator-uat -o yaml > secret-kafka-bkup.yaml
```

```bash
kubectl get secret secret-kafka -n operator-uat -o yaml > secret-kafka-backup-$(date +%Y%m%d-%H%M%S).yaml
```

**What this does**: 
- Creates a backup of the current secret
- First command: Simple backup with fixed filename
- Second command: Timestamped backup for version tracking
- `$(date +%Y%m%d-%H%M%S)`: Creates timestamp (YYYYMMDD-HHMMSS format)

**Backup Location**: Current directory where command is run

**Why backup?**: 
- Allows rollback if secret update causes issues
- Provides audit trail of changes
- Documents previous credentials

### Step 7.3: Prepare New Credentials

For DR cluster credentials, you need to create the correct format:

```bash
echo 'dXNlcm5hbWU9QUJHTTNSUUdLUUwyN0hWNQpwYXNzd29yZD00QVBFUGxCNzlMT1V3N3k5dkg2eHdPK2J1OXBwQVlkSlEyeXJTenFReTFrYlJneS9jZ29XTW1GakpRbGxCTjFZCg==' | base64 -d
```

**What this does**: 
- Decodes a base64-encoded credential string
- Shows the actual username and password format
- Helpful for understanding the credential structure

**Output Format**:
```
username=ABGM3RQGKQL27HV5
password=4APEPlB79LOUw7y9vH6xwO+bu9ppAYdJQ2yrSzqQy1kbRgy/cgoWMmFjJQllBN1Y
```

### Step 7.4: Create Plain Text Credentials File

```bash
vi plain.txt
```

**What this does**: 
- Opens a text editor to create/edit the credentials file
- Used as temporary storage for credentials during updates

**File Content** (for new DR credentials):
```
username=<DR_KAFKA_USERNAME>
password=<DR_KAFKA_PASSWORD>
```

**Replace with**:
- `<DR_KAFKA_USERNAME>`: Username for DR Kafka cluster
- `<DR_KAFKA_PASSWORD>`: Password for DR Kafka cluster

### Step 7.5: Encode Credentials for Kubernetes Secret

```bash
echo -e "username=S2GBQE6RGXJL7C2O\npassword=cflt4YIyZJ4EWkAvKLFi32YHrATE1KHvCBPP5TphdBHbyBg0bKYiSXIzBiNZ63OA" | base64 -w0
```

**What this does**: 
- Creates a formatted credential string
- `echo -e`: Interprets escape sequences (`\n` = newline)
- `base64 -w0`: Encodes to base64 without line wrapping
- Output is ready to paste into Kubernetes secret

**Expected Output** (single line):
```
dXNlcm5hbWU9UzJHQlFFNlJHWEpMN0MyTwpwYXNzd29yZD1jZmx0NFlJeVpKNEVXa0F2S0xGaTMyWUhyQVRFMUtIdkNCUFA1VHBoZEJIYnlCZzBiS1lpU1hJekJpTlo2M09BCg==
```

### Step 7.6: Edit Kubernetes Secret

```bash
kubectl edit secret secret-kafka -n operator-uat
```

**What this does**: 
- Opens the secret in your default editor (vi/nano)
- Allows in-place editing of the secret
- `-n operator-uat`: Specifies the namespace

**Steps in Editor**:
1. Find the `data:` section
2. Locate the `username` and `password` fields
3. Replace the base64-encoded values with new DR credentials
4. Save and exit (`:wq` in vi)

**Important**: 
- Do NOT edit metadata or other fields
- Only modify the `data:` section values
- Ensure proper YAML indentation

### Step 7.7: Verify Secret Update

```bash
kubectl get secret secret-kafka -n operator-uat -o yaml
```

**What this does**: 
- Confirms the secret was updated
- Shows new encoded credentials
- Verifies YAML structure is intact

### Alternative: Patch Method (Advanced)

If preferred, use JSON patch instead of manual editing:

```bash
kubectl patch secret es-conf-platform-uat-secret \
  -n operator-uat \
  --type='json' \
  -p="[{'op': 'replace', 'path': '/data/snowflake-private-key.p8', 'value': 'LS0tLS1CRUdJTi...'}]"
```

**What this does**: 
- Patches a specific field in the secret
- `--type='json'`: Specifies JSON Patch format
- `'op': 'replace'`: Operation type (replace value)
- `'path': '/data/...'`: Field to update
- `'value': '...'`: New base64-encoded value

**When to Use**:
- For scripted/automated secret updates
- When updating single fields
- For CI/CD pipeline integration

### Step 7.8: Verify Connector Pod Connectivity

After updating secrets, restart connector pods to load new credentials:

```bash
kubectl get pods -l app=connectors -n operator-uat
```

Wait for pods to restart automatically, then verify:

```bash
kubectl logs connectors-2 -n operator-uat
```

**What this does**: 
- Shows container logs for the connector pod
- Look for successful connection messages to DR broker
- Should show no authentication errors

**Expected Log Patterns**:
```
[INFO] Kafka cluster bootstrapped successfully
[INFO] Broker connection established: lkc-xqrk0kz
[INFO] Consumer group initialized
```

**Error Patterns** (troubleshoot):
```
[ERROR] SASL authentication failed
[ERROR] Invalid credentials
[ERROR] Broker not reachable
```

---

## Step-by-Step Deployment Summary

| Phase | Step | Action | Command | Status |
|-------|------|--------|---------|--------|
| 1 | 1.1 | Auth to Confluent | `confluent login --no-browser` | Done |
| 1 | 1.2 | List environments | `confluent environment list` | Done |
| 1 | 1.3 | Select DR environment | `confluent environment use env-xrwzz` | Done |
| 1 | 1.4 | Verify networks | `confluent network list` | Done |
| 1 | 1.5 | List clusters | `confluent kafka cluster list` | Done |
| 2 | 2.1 | Check existing links | `confluent kafka link list --cluster ...` | Done |
| 2 | 2.2 | Create cluster link | `confluent kafka link create ...` | Done |
| 2 | 2.3 | Verify link | `confluent kafka link list --cluster ...` | Done |
| 3 | 3.1 | Mirror topics | `confluent kafka mirror create ...` | Done |
| 3 | 3.2 | Verify mirrors | `confluent kafka topic describe ...` | Done |
| 4 | 4.1 | Auth to Confluent | `confluent login --no-browser` | Done |
| 4 | 4.2 | Select DR environment | `confluent environment use env-xrwzz` | Done |
| 4 | 4.3 | Create schema exporter | `confluent schema-registry exporter create ...` | Done |
| 4 | 4.4 | List exporters | `confluent schema-registry exporter list` | Done |
| 4 | 4.5 | Check status | `confluent schema-registry exporter status describe ...` | Done |
| 4 | 4.6 | View details | `confluent schema-registry exporter describe ...` | Done |
| 5 | 5.1 | Promote topics | `confluent kafka mirror promote ...` | Done |
| 6 | 6.1 | Set AWS profile | `export AWS_PROFILE=DEVCICD` | Done |
| 6 | 6.2 | Update kubeconfig | `aws eks update-kubeconfig ...` | Done |
| 6 | 6.3 | Verify cluster | `kubectl get nodes` | Done |
| 6 | 6.4 | List all pods | `kubectl get pods --all-namespaces` | Done |
| 6 | 6.5 | Get connector pods | `kubectl get pods -l app=connectors ...` | Done |
| 7 | 7.1 | View secret | `kubectl get secret secret-kafka -o yaml` | Done |
| 7 | 7.2 | Backup secret | `kubectl get secret ... > backup.yaml` | Done |
| 7 | 7.3 | Prepare credentials | `echo ... | base64 -d` | Done |
| 7 | 7.4 | Create credentials file | `vi plain.txt` | Done |
| 7 | 7.5 | Encode credentials | `echo ... | base64 -w0` | Done |
| 7 | 7.6 | Edit secret | `kubectl edit secret secret-kafka ...` | Done |
| 7 | 7.7 | Verify update | `kubectl get secret ... -o yaml` | Done |
| 7 | 7.8 | Check logs | `kubectl logs connectors-2 ...` | Done |

---

## Troubleshooting

### Issue: Cluster Link Creation Fails

**Symptoms**: 
- Command fails with error during `confluent kafka link create`

**Causes**:
- Incorrect source cluster ID
- Missing or invalid API credentials in config file
- Network connectivity issues
- Security group/firewall restrictions

**Resolution**:
1. Verify cluster IDs:
   ```bash
   confluent kafka cluster list
   ```
2. Test credentials manually:
   ```bash
   confluent kafka cluster describe <CLUSTER_ID>
   ```
3. Check config file syntax
4. Verify network connectivity to source cluster

---

### Issue: Topics Not Replicating

**Symptoms**: 
- Topics mirrored but no data appearing on DR cluster
- Mirror status shows 0 messages

**Causes**:
- Cluster link not fully established
- Network latency/lag
- Cluster link misconfiguration
- Source topic is empty

**Resolution**:
1. Verify cluster link status:
   ```bash
   confluent kafka link list --cluster lkc-xqrk0kz
   ```
2. Check topic replication lag:
   - Use Confluent Cloud UI to monitor replication metrics
3. Verify source topic has data:
   ```bash
   confluent kafka topic describe <TOPIC_NAME> --cluster <PROD_CLUSTER>
   ```
4. Recreate mirror if necessary:
   ```bash
   confluent kafka mirror delete <TOPIC_NAME> --link cl-prod-to-dr --cluster lkc-xqrk0kz
   confluent kafka mirror create <TOPIC_NAME> --link cl-prod-to-dr --cluster lkc-xqrk0kz
   ```

---

### Issue: Schema Registry Exporter Not Working

**Symptoms**: 
- Exporter shows status but schemas not synced
- Error message about unavailable schemas

**Causes**:
- Incorrect schema registry URLs
- Invalid API credentials
- Network access issues
- Schema context mismatch

**Resolution**:
1. Verify exporter configuration:
   ```bash
   confluent schema-registry exporter describe prod-to-dr-schema-exporter
   ```
2. Test schema registry connectivity:
   ```bash
   curl -u <API_KEY>:<API_SECRET> \
     https://psrc-prod.region.provider.confluent.cloud/subjects
   ```
3. Check schema registry logs in Confluent Cloud UI
4. Verify context name matches source environment

---

### Issue: Kafka Connect Cannot Connect to DR Cluster

**Symptoms**: 
- Connector tasks fail
- Logs show "Unable to connect to broker"
- Authentication errors in pod logs

**Causes**:
- Incorrect broker bootstrap servers
- Invalid or expired credentials in secret
- Network connectivity from EKS to Confluent Cloud
- Security group/firewall rules

**Resolution**:
1. Verify current secret:
   ```bash
   kubectl get secret secret-kafka -n operator-uat -o yaml
   ```
2. Decode and verify credentials:
   ```bash
   kubectl get secret secret-kafka -n operator-uat -o jsonpath='{.data.username}' | base64 -d
   ```
3. Update secret with correct DR credentials (see Phase 7)
4. Verify bootstrap servers in connector configuration
5. Check EKS security groups allow outbound to Confluent Cloud
6. Restart connector pod:
   ```bash
   kubectl delete pod connectors-0 -n operator-uat
   ```

---

### Issue: Topic Promotion Fails

**Symptoms**: 
- Promotion command returns error
- Topic remains read-only after promotion attempt

**Causes**:
- Replication not complete
- Cluster link misconfigured
- Insufficient permissions

**Resolution**:
1. Verify replication status:
   ```bash
   confluent kafka topic describe <TOPIC_NAME> --cluster lkc-xqrk0kz
   ```
2. Wait for replication to complete if lag exists
3. Check cluster link is READY:
   ```bash
   confluent kafka link list --cluster lkc-xqrk0kz
   ```
4. Verify you have appropriate permissions (cluster admin role)
5. Try promotion again after replication complete

---

### Issue: High Replication Latency

**Symptoms**: 
- Data appears on DR cluster after significant delay
- Replication lag metric increasing

**Causes**:
- Network bandwidth limitations
- Cluster link network performance
- Large topic volumes overwhelming replication

**Resolution**:
1. Monitor replication lag in Confluent Cloud UI
2. Check network connectivity between clusters
3. Optimize topic configuration:
   - Reduce retention if possible
   - Compress messages
   - Increase cluster link throughput (if available)
4. Prioritize critical topics for mirroring
5. Scale DR cluster resources if needed

---

### Issue: Secret Update Causes Connector Crashes

**Symptoms**: 
- Connector pods keep restarting
- Logs show credential errors
- State: CrashLoopBackOff

**Causes**:
- Malformed base64 encoding
- Incorrect secret key names
- YAML syntax error in secret
- Connector restart policy kicking in

**Resolution**:
1. Restore from backup:
   ```bash
   kubectl apply -f secret-kafka-bkup.yaml
   ```
2. Restart pod to use old credentials
3. Review secret syntax carefully before applying
4. Ensure base64 encoding has no whitespace
5. Use patch method instead of manual edit if possible
6. Apply changes gradually and test

---

## Best Practices

### 1. Planning
- [ ] Document all topic names that need mirroring
- [ ] Identify critical vs non-critical topics
- [ ] Plan for phased rollout (test → staging → production)
- [ ] Schedule during low-traffic windows
- [ ] Communicate with application teams

### 2. Testing
- [ ] Test cluster link with non-critical topics first
- [ ] Verify replication accuracy with data validation
- [ ] Test connector failover in non-production environment
- [ ] Validate schema registry sync with sample schemas
- [ ] Test DR cluster failover scenarios

### 3. Documentation
- [ ] Document cluster IDs and environment IDs
- [ ] Keep records of all configuration files
- [ ] Document API keys and credentials separately (encrypted)
- [ ] Maintain runbooks for failover procedures
- [ ] Document any custom configurations

### 4. Security
- [ ] Rotate API keys regularly
- [ ] Store credentials in secure vaults (not in code)
- [ ] Use separate credentials for prod and DR
- [ ] Audit secret access and changes
- [ ] Encrypt backups

### 5. Monitoring
- [ ] Set up alerts for replication lag
- [ ] Monitor cluster link health
- [ ] Track schema export completion
- [ ] Monitor connector pod health
- [ ] Set up dashboards for DR metrics

### 6. Disaster Recovery Testing
- [ ] Perform regular DR drills (monthly)
- [ ] Test failover procedures end-to-end
- [ ] Validate data integrity post-failover
- [ ] Document RTO and RPO metrics
- [ ] Update runbooks based on test findings

---

## Rollback Procedures

### If Cluster Link Creation Fails

1. Delete the failed cluster link:
   ```bash
   confluent kafka link delete cl-prod-to-dr --cluster lkc-xqrk0kz
   ```
2. Fix configuration issues
3. Recreate cluster link with corrected settings

### If Topic Mirroring Has Issues

1. Delete the problematic mirror:
   ```bash
   confluent kafka mirror delete <TOPIC_NAME> --link cl-prod-to-dr --cluster lkc-xqrk0kz
   ```
2. Verify data integrity on source
3. Recreate mirror once issues resolved

### If Secret Update Breaks Connectors

1. Immediately restore backup:
   ```bash
   kubectl apply -f secret-kafka-bkup.yaml
   ```
2. Restart connector pods:
   ```bash
   kubectl delete pod connectors-0 -n operator-uat
   ```
3. Review changes and retry after testing

---

## Estimated Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Phase 1 (Cluster Setup) | 2-4 hours | Mostly waiting for cluster provisioning |
| Phase 2 (Cluster Link) | 1-2 hours | Usually quick, dependent on network config |
| Phase 3 (Topic Mirroring) | 2-12 hours | Depends on topic volume and count |
| Phase 4 (Schema Sync) | 1-2 hours | Typically very quick |
| Phase 5 (Topic Promotion) | 15 minutes | Quick, one-time operation per topic |
| Phase 6 (EKS Access) | 30 minutes | Configuration and verification |
| Phase 7 (Secret Updates) | 1-2 hours | Testing and validation |
| **Total Timeline** | **1-2 weeks** | Includes testing and validation |

---

## Appendix: Quick Reference Commands

### Confluent CLI Commands

```bash
# Authentication
confluent login --no-browser
confluent logout

# Environment Management
confluent environment list
confluent environment use <ENV_ID>
confluent environment describe <ENV_ID>

# Cluster Management
confluent kafka cluster list
confluent kafka cluster describe <CLUSTER_ID>

# Cluster Links
confluent kafka link list --cluster <CLUSTER_ID>
confluent kafka link describe <LINK_NAME> --cluster <CLUSTER_ID>
confluent kafka link delete <LINK_NAME> --cluster <CLUSTER_ID>

# Topic Mirroring
confluent kafka mirror list --link <LINK_NAME> --cluster <CLUSTER_ID>
confluent kafka mirror describe <TOPIC_NAME> --link <LINK_NAME> --cluster <CLUSTER_ID>
confluent kafka mirror delete <TOPIC_NAME> --link <LINK_NAME> --cluster <CLUSTER_ID>

# Schema Registry
confluent schema-registry exporter list
confluent schema-registry exporter describe <EXPORTER_NAME>
confluent schema-registry exporter status describe <EXPORTER_NAME>
```

### Kubernetes Commands

```bash
# Cluster Access
aws eks update-kubeconfig --region <REGION> --name <CLUSTER_NAME>
kubectl cluster-info

# Pod Management
kubectl get pods -n <NAMESPACE>
kubectl get pods -l <LABEL> -n <NAMESPACE>
kubectl describe pod <POD_NAME> -n <NAMESPACE>
kubectl logs <POD_NAME> -n <NAMESPACE>

# Secret Management
kubectl get secret <SECRET_NAME> -n <NAMESPACE> -o yaml
kubectl edit secret <SECRET_NAME> -n <NAMESPACE>
kubectl patch secret <SECRET_NAME> -n <NAMESPACE> --type='json' -p=[...]
kubectl delete secret <SECRET_NAME> -n <NAMESPACE>
```

### Useful One-Liners

```bash
# Get all secrets in namespace
kubectl get secrets -n operator-uat

# Decode specific secret field
kubectl get secret <SECRET_NAME> -n <NAMESPACE> -o jsonpath='{.data.<FIELD>}' | base64 -d

# Get pod image versions
kubectl get pods -n <NAMESPACE> -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].image}{"\n"}{end}'

# Get recent pod events
kubectl describe pod <POD_NAME> -n <NAMESPACE> | grep -A 20 Events

# Restart all pods in deployment
kubectl rollout restart deployment/<DEPLOYMENT_NAME> -n <NAMESPACE>
```

---

## Support & Further Help

### Confluent Cloud Documentation
- https://docs.confluent.io/cloud/current/overview.html
- https://docs.confluent.io/cloud/current/clusters/cluster-link/overview.html

### AWS EKS Documentation
- https://docs.aws.amazon.com/eks/latest/userguide/

### Kubernetes Documentation
- https://kubernetes.io/docs/

### When to Contact Support

Contact Confluent Support if:
- Cluster link creation fails repeatedly
- Replication lag exceeds expected thresholds
- Schema registry exporter reports errors
- Network connectivity issues between clusters

Contact AWS Support if:
- EKS cluster access issues
- Network/security group configuration problems
- IAM permission issues

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Sept 1, 2026 | DR Setup Team | Initial comprehensive guide based on production implementation |

---

## Conclusion

This document provides a complete, reproducible process for setting up Disaster Recovery infrastructure using Confluent Cloud and Kafka Connect on AWS EKS. By following these steps in order and understanding the reasoning behind each step, any team member should be able to replicate this setup in their own environment.

**Key Takeaways**:
1. DR setup requires coordination across multiple platforms (Confluent Cloud, AWS, Kubernetes)
2. Each phase builds on previous phases - do not skip steps
3. Comprehensive testing and validation at each phase is essential
4. Backup and document everything for troubleshooting
5. Regular DR drills ensure team readiness for actual failover scenarios

---

*This guide was created based on actual production implementation and command history from Aug 10 - Aug 31, 2026.*
