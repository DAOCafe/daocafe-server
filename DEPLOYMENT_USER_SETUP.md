# Setting Up a Dedicated Deployment User for CI/CD

This document provides step-by-step instructions for setting up a dedicated deployment user with SSH key authentication for your CI/CD pipeline on your DigitalOcean droplet.

## Why Use a Dedicated Deployment User?

Using a dedicated deployment user instead of root provides several benefits:

1. **Security**: Following the principle of least privilege reduces risk if credentials are compromised
2. **Audit Trail**: Makes it easier to track deployment activities in system logs
3. **Easier Maintenance**: Allows key rotation without affecting the root account
4. **Best Practice**: Many security standards recommend disabling direct root SSH access

## Step 1: Create a Deployment User

Connect to your DigitalOcean droplet as root or with a user that has sudo privileges:

```bash
# Create a new user called 'deploy'
sudo adduser deploy

# Follow the prompts to set a strong password
# You can skip the user information fields by pressing Enter
```

## Step 2: Set Up the Deployment Directory

Create the deployment directory and set proper permissions:

```bash
# Create the deployment directory
sudo mkdir -p /home/deploy/daocafe-server

# Set ownership to the deploy user
sudo chown -R deploy:deploy /home/deploy/daocafe-server
```

## Step 3: Generate SSH Key Pair

On your local machine (not the server), generate a new SSH key pair specifically for deployments:

```bash
# Generate a new ED25519 SSH key (more secure than RSA)
ssh-keygen -t ed25519 -C "github-deploy@dao.cafe"

# Save it to a specific file like ~/.ssh/daocafe_deploy_key
# DO NOT use an existing key that you use for other purposes
```

## Step 4: Add the Public Key to the Server

Copy the public key to your server:

```bash
# Display your public key
cat ~/.ssh/daocafe_deploy_key.pub

# Copy the output to your clipboard
```

On your server:

```bash
# Switch to the deploy user
sudo su - deploy

# Create the .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Create or append to the authorized_keys file
nano ~/.ssh/authorized_keys

# Paste your public key, save and exit (Ctrl+X, Y, Enter)

# Set proper permissions
chmod 600 ~/.ssh/authorized_keys

# Exit back to your original user
exit
```

## Step 5: Test the SSH Connection

From your local machine:

```bash
# Try connecting with the new key
ssh -i ~/.ssh/daocafe_deploy_key deploy@YOUR_SERVER_IP

# If successful, you should be logged in as the deploy user
```

## Step 6: Add the Private Key to GitHub Secrets

1. Display your private key:
   ```bash
   cat ~/.ssh/daocafe_deploy_key
   ```

2. Copy the entire output, including the `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----` lines.

3. Go to your GitHub repository → Settings → Secrets and variables → Actions

4. Add the following secrets:
   - `PROD_HOST`: Your DigitalOcean droplet IP
   - `PROD_USERNAME`: `deploy` (the new user)
   - `PROD_SSH_KEY`: The private key content (the entire file including BEGIN and END lines)

## Step 7: Grant Necessary Permissions

The deploy user needs permission to run Docker commands:

```bash
# Add the deploy user to the docker group
sudo usermod -aG docker deploy

# Create a sudoers file for the deploy user with limited permissions
echo "deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/deploy

# Set proper permissions on the sudoers file
sudo chmod 440 /etc/sudoers.d/deploy
```

## Step 8: Enhance SSH Security (Optional but Recommended)

Edit the SSH configuration:

```bash
sudo nano /etc/ssh/sshd_config
```

Make the following changes:

```
# Disable root login
PermitRootLogin no

# Disable password authentication (use keys only)
PasswordAuthentication no

# Limit SSH access to specific users (optional)
AllowUsers deploy your_admin_user
```

Restart SSH:

```bash
sudo systemctl restart sshd
```

## Step 9: Verify Your CI/CD Pipeline

1. Make a small change to your repository
2. Push it to the development branch
3. Verify that tests run successfully
4. Create and merge a PR to main
5. Verify that the deployment to production works correctly

## Troubleshooting

If deployments fail, check:

1. SSH access: `ssh -i ~/.ssh/daocafe_deploy_key -v deploy@YOUR_SERVER_IP`
2. Permissions: Ensure the deploy user has access to the deployment directory
3. Docker permissions: Verify the deploy user can run Docker commands
4. GitHub secrets: Check that all secrets are correctly set
5. Server logs: `sudo journalctl -u sshd` to check for SSH connection issues

## Security Considerations

1. Regularly rotate your SSH keys (e.g., every 90 days)
2. Monitor failed login attempts: `sudo journalctl -u sshd | grep "Failed"`
3. Consider setting up SSH key passphrase for additional security
4. Use a firewall (UFW) to limit SSH access to specific IP ranges if possible
