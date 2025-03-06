# GitHub CI/CD Pipeline Setup

This document explains the GitHub Actions CI/CD pipeline setup for the daocafe-server project, which implements a workflow where:

1. The `main` branch is protected
2. Code is built and deployed to a development environment when pushed to the `development` branch
3. Code is built and deployed to production when a pull request to `main` is successful

## Pipeline Overview

The CI/CD pipeline is defined in `.github/workflows/ci-cd.yml` and consists of the following jobs:

```
┌─────────┐     ┌─────────────────┐     ┌─────────────────────┐
│  Test   │ ──► │ Build and Push  │ ──► │ Deploy Development  │
└─────────┘     └─────────────────┘     └─────────────────────┘
                        │
                        │                ┌─────────────────────┐
                        └───────────────►│ Deploy Production   │
                                         └─────────────────────┘
```

- **Test**: Runs the Django test suite against a PostgreSQL and Redis service
- **Build and Push**: Builds a Docker image and pushes it to GitHub Container Registry
- **Deploy Development**: Deploys to the development environment when code is pushed to the `development` branch
- **Deploy Production**: Deploys to the production environment when a pull request to `main` is merged

## Environment Configuration

The pipeline uses the environment-based configuration we've set up:

- For the development environment, it uses `.env.development`
- For the production environment, it uses `.env.production`

This ensures that the appropriate settings (JWT lifetimes, debug mode, etc.) are used in each environment.

## GitHub Repository Setup

To use this pipeline, you need to configure your GitHub repository:

1. **Protect the `main` branch**:
   - Go to Settings > Branches
   - Add a branch protection rule for `main`
   - Enable "Require pull request reviews before merging"
   - Enable "Require status checks to pass before merging"
   - Select the "test" and "build-and-push" status checks

2. **Create GitHub Environments**:
   - Go to Settings > Environments
   - Create two environments: `development` and `production`
   - For the `production` environment, enable "Required reviewers" for additional security

3. **Add Repository Secrets**:
   - Go to Settings > Secrets and variables > Actions
   - Add the following secrets:
     - `DEV_HOST`: Hostname of your development server
     - `DEV_USERNAME`: SSH username for your development server
     - `DEV_SSH_KEY`: SSH private key for your development server
     - `PROD_HOST`: Hostname of your production server
     - `PROD_USERNAME`: SSH username for your production server
     - `PROD_SSH_KEY`: SSH private key for your production server

## Deployment Process

### Development Deployment

When code is pushed to the `development` branch:

1. Tests are run
2. A Docker image is built and pushed to GitHub Container Registry
3. The image is deployed to the development server using SSH
4. The application is started with `DJANGO_ENV_FILE=.env.development`

### Production Deployment

When a pull request to `main` is merged:

1. Tests are run
2. A Docker image is built and pushed to GitHub Container Registry
3. The image is deployed to the production server using SSH
4. The application is started with `DJANGO_ENV_FILE=.env.production`

## Server Setup

On both development and production servers, you need to:

1. Create a deployment directory
2. Copy your `docker-compose.yml` file
3. Create the appropriate `.env.development` or `.env.production` file
4. Ensure Docker and Docker Compose are installed

The CI/CD pipeline will handle pulling the latest image and restarting the containers.

## Customizing the Pipeline

You may need to customize the pipeline for your specific needs:

- Update the Python version in the "Set up Python" step
- Modify the deployment scripts to match your server configuration
- Add additional test or build steps as needed
- Configure notifications for deployment success/failure

## Troubleshooting

If deployments fail, check:

1. SSH access to your servers
2. Docker and Docker Compose installation on your servers
3. GitHub repository secrets
4. Environment files on your servers
