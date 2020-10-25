#!/bin/bash

echo "Creating resource group $RESOURCE_GROUP"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION

echo "Creating registry ${REGISTRY}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --location "$LOCATION" \
    --subscription "$SUBSCRIPTION" \
    --name $REGISTRY \
    --admin-enabled true --sku Basic \
    --verbose

echo "Publishing ${IMAGE} to ${REGISTRY}"
az acr build \
    --registry $REGISTRY \
    --image $IMAGE .

echo "Creating k8s cluster $K8S_CLUSTER"
az aks create \
    --subscription "$SUBSCRIPTION" \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --name $K8S_CLUSTER \
    --node-count 3 \
    --attach-acr $REGISTRY \
    --dns-name-prefix condesa \
    --kubernetes-version 1.19.0 \
    --load-balancer-sku Standard \
    --outbound-type loadBalancer \
    --network-plugin kubenet \
    --node-osdisk-size 50 \
    --node-vm-size Standard_B2ms \
    --vm-set-type VirtualMachineScaleSets \
    --zones 1 2 3 \
    --no-ssh-key
    # --generate-ssh-keys \
    # --admin-username azureuser \
    # --disable-rbac \
    # --enable-addons monitoring \

echo "Getting credentials"
az aks get-credentials \
    --resource-group $RESOURCE_GROUP \
    --name $K8S_CLUSTER \
    --overwite-existing

echo "Creating Azure file shares secret for $AKS_PERS_STORAGE_ACCOUNT_NAME"
kubectl create secret generic \
    az-file-secret \
    --from-literal=azurestorageaccountname=$AKS_PERS_STORAGE_ACCOUNT_NAME \
    --from-literal=azurestorageaccountkey=$STORAGE_KEY