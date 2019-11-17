# gitsup-gcloud-deployment

Auto-update of git submodules of projects hosted on Github using [gitsup](
https://github.com/tgamauf/gitsup) and [Google Cloud Functions](
https://cloud.google.com/functions/docs/).

## Quickstart
1. Create a [Github personal access token](https://github.blog/2013-05-16-personal-api-tokens/) 
and store it in an environment variable ` PLAINTEXT_GITHUB_API_TOKEN="<Github personal access token in plaintext>"`
2. Create a random secret that is used to authorize your webhook call and store it in an environment 
variable `PLAINTEXT_GITHUB_WEBHOOK_SECRET="<Github webhook secret in plaintext>"`
3. Store your repository information in environment variables (see [gitsup docs](
https://github.com/tgamauf/gitsup) for all config options):
    ```
    GITSUP_OWNER=<your Github name>
    GITSUP_REPOSITORY=<your Github repository>
    GITSUP_SUBMODULES="<comma separated list of submodules in your repository>"
    ```
4. Download a zip archive of this repository and extract it, then store the extracted path (the path 
to `main.py`) in an environment variable: `SOURCE=<path to source code>`
5. Set environment variables that define how your cloud function is named and where it will be
deployed:
    ```
    # Cloud function parameters
    APP=<app name>
    PROJECT=<Google Cloud project>
    # One of the locations you get via `gcloud kms locations list`
    LOCATION=<region>
    
    # These variable names can be changed according to your needs
    # This is just a sensible name, but you can choose it freely
    KEYRING=serverless-secrets
    # I use the app name as it is easier to see what belongs together,
    #  but this isn't necessary or usefull if several cloud functions
    #  are used
    KEY=${APP}
    # I use the app name as it is easier to see what belongs together,
    #  but this isn't necessary or usefull if several cloud functions
    #  are used
    SERVICE_ACCOUNT_NAME=${APP}
    SERVICE_ACCOUNT=${SERVICE_ACCOUNT_NAME}@${PROJECT}.iam.gserviceaccount.com
    MEMORY=128MB
    RUNTIME=python37
    ENVIRONMENT_FILE=env.yaml
    MAX_INSTANCES=5
    ```
2. Create keyring and key that are used to encrypt/decrypt the secrets used by the cloud 
function. It is possible that you have to activate the 
Key Management Service (KMS) API first [here](https://console.cloud.google.com/security/kms):
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
5. Create the environment config
    ```
    echo "KMS_CRYPTO_KEY_ID=projects/${PROJECT}/locations/${LOCATION}/keyRings/${KEYRING}/cryptoKeys/${KEY}" > "${ENVIRONMENT_FILE}"
    echo "GITHUB_API_TOKEN=${GITHUB_API_TOKEN}" >> "${ENVIRONMENT_FILE}"
    echo "GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}" >> "${ENVIRONMENT_FILE}"
    
    # Careful, it is GITSUP, not GITHUP
    echo "GITSUP_OWNER=${GITSUP_OWNER}" >> "${ENVIRONMENT_FILE}"
    echo "GITSUP_REPOSITORY=${GITSUP_REPOSITORY}" >> "${ENVIRONMENT_FILE}"
    echo "GITSUP_SUBMODULES=${GITSUP_SUBMODULES}" >> "${ENVIRONMENT_FILE}"
    ```
6. Create service account and set roles. It is possible that you have to activate the IAM API 
first [here](https://console.cloud.google.com/iam-admin/iam):
    ```
    gcloud iam service-accounts create ${SERVICE_ACCOUNT}
    gcloud kms keys add-iam-policy-binding generate-submodule-autoupdate \
        --location=${LOCATION} \
        --keyring=${KEYRING} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role roles/cloudkms.cryptoKeyDecrypter
    ```
5. Deploy cloud function. It is possible that you have to activate the functions API first 
[here](https://console.cloud.google.com/functions):
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
6. All data about the cloud function is printed by the deploy command. What you need is the `url` 
(it should be `url: https://${REGION}-${PROJECT}.cloudfunctions.net/${APP}`)
6. For each submodule of your parent repository add the url as [Github webhook](
https://developer.github.com/webhooks/). Set the url from the last step as `Payload URL`, the 
`Content type` to `application/json`, and the secret you created in step 2 as `Secret`.

Github will automatically trigger a request for testing purposes and you should see a green tickmark 
if everything is ok.
