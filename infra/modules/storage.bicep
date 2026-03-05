// ──────────────────────────────────────────────
// Storage Account module – StorageV2, Standard_LRS
// ──────────────────────────────────────────────

@description('Environment name used in resource naming.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to resources.')
param tags object = {}

// Storage account names must be 3-24 chars, lowercase alphanumeric only.
// uniqueString() generates a deterministic 13-char hash from the resource group ID,
// ensuring global uniqueness while being stable across redeployments.
var storageAccountName = 'stforms${take(uniqueString(resourceGroup().id), 8)}'

// ──────────────────────────────────────────────
// Storage Account
// ──────────────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false  // Managed identity only — no shared keys
    defaultToOAuthAuthentication: true
  }
}

// ──────────────────────────────────────────────
// Blob service & containers
// ──────────────────────────────────────────────

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource formRegistryContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'form-registry'
  properties: {
    publicAccess: 'None'
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────

@description('Name of the Storage Account.')
output storageAccountName string = storageAccount.name

@description('Resource ID of the Storage Account.')
output storageAccountId string = storageAccount.id

@description('Primary blob endpoint.')
output primaryBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob
