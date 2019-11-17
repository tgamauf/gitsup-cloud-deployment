# gitsup-gcloud-deployment

Auto-update of git submodules of projects hosted on Github using gitsup and Google Cloud Functions.

## Quickstart

1. Set environment variables
    ```
    export APP=<app name>
    export PROJECT=<Google Cloud project>
    # One of the locations you get via `gcloud kms locations list`
    export LOCATION=<region>
    # This is just a sensible name, but you can choose it freely
    export KEYRING=serverless-secrets
    # I use the app name as it is easier to see what belongs together,
    #  but this isn't necessary or usefull if several cloud functions
    #  are used
    export KEY=${APP}
    # I use the app name as it is easier to see what belongs together,
    #  but this isn't necessary or usefull if several cloud functions
    #  are used
    export SERVICE_ACCOUNT_NAME=${APP}
    export SERVICE_ACCOUNT=${SERVICE_ACCOUNT_NAME}@${PROJECT}.iam.gserviceaccount.com
    export MEMORY=128MB
    export RUNTIME=python37
    # Format: https://source.developers.google.com/projects/<project>/repos/<repo>
    export SOURCE=<Google Source Repository path>
    export ENVIRONMENT_FILE=env.yaml
    export MAX_INSTANCES=5
    ```
2. Create keyring and key
    ```
    gcloud kms keyrings create \
        --location=${LOCATION} \
        ${KEYRING}
    gcloud kms keys create \
        --location=${LOCATION} \
        --keyring=${KEYRING} \
        --purpose=encryption \
        ${KEY}
    ```
3. Encode secrets
    ```
    GITHUB_API_TOKEN=$(echo "<plaintext Github personal access token>" \
        | gcloud kms encrypt \
        --location=${LOCATION} \
        --keyring=${KEYRING} \
        --key=${KEY} \
        --ciphertext-file=- \
        --plaintext-file=- \
        | base64)
    GITHUB_WEBHOOK_SECRET=$(echo "<plaintext Github webhook secret>" \
        | gcloud kms encrypt \
        --location=${LOCATION} \
        --keyring=${KEYRING} \
        --key=${KEY} \
        --ciphertext-file=- \
        --plaintext-file=- \
        | base64)
    ```
4. Create service account and set roles
    ```
    gcloud iam service-accounts create ${SERVICE_ACCOUNT}
    gcloud kms keys add-iam-policy-binding generate-submodule-autoupdate \
        --location=${LOCATION} \
        --keyring=${KEYRING} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role roles/cloudkms.cryptoKeyDecrypter
    ```
5. Deploy cloud function
    ```
    gcloud functions deploy ${APP} \
        --region=${REGION} \
        --allow-unauthenticated \
        --entry-point autoupdate \
        --memory=${MEMORY} \
        --runtime=${RUNTIME} \
        --service-account=${SERVICE_ACCOUNT} \
        --source=${SOURCE} \
        --env-vars-file="${ENVIRONMENT_FILE}" \
        --max-instances=5 \
        --trigger-http
    ```
