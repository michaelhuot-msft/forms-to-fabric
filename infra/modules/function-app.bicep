// ──────────────────────────────────────────────
// Function App module – Linux Consumption (Python 3.11)
// ──────────────────────────────────────────────

@description('Environment name used in resource naming.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to resources.')
param tags object = {}

@description('Name of the Storage Account used for AzureWebJobsStorage.')
param storageAccountName string

@description('Application Insights instrumentation key.')
param appInsightsInstrumentationKey string

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('Name of the Key Vault for secret references.')
param keyVaultName string

@description('Microsoft Fabric OneLake endpoint URL.')
param onelakeEndpoint string

@description('Path to the form-registry configuration inside the storage container.')
param formRegistryPath string

// ──────────────────────────────────────────────
// Existing resources
// ──────────────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Function App names are globally unique. Add a hash suffix.
var suffix = take(uniqueString(resourceGroup().id), 6)

// ──────────────────────────────────────────────
// Consumption plan (Y1)
// ──────────────────────────────────────────────

resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'asp-forms-${environmentName}'
  location: location
  tags: tags
  kind: 'linux'
  properties: {
    reserved: true
  }
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
}

// ──────────────────────────────────────────────
// Function App
// ──────────────────────────────────────────────

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: 'func-forms-${environmentName}-${suffix}'
  location: location
  tags: union(tags, { 'azd-service-name': 'functions' })
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          // Use managed identity for storage — no shared keys needed
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccount.name
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsightsInstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'KEY_VAULT_URL'
          value: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}'
        }
        {
          name: 'ONELAKE_ENDPOINT'
          value: onelakeEndpoint
        }
        {
          name: 'FORM_REGISTRY_PATH'
          value: formRegistryPath
        }
      ]
    }
  }
}

// ──────────────────────────────────────────────
// Role assignments – managed identity → storage
// ──────────────────────────────────────────────

// Storage Blob Data Owner (read/write blobs for AzureWebJobsStorage)
resource storageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  }
}

// Storage Account Contributor (manage file shares for consumption plan)
resource storageAccountContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, 'StorageAccountContributor')
  scope: storageAccount
  properties: {
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab')
  }
}

// Storage Queue Data Contributor (Azure Functions uses queues internally)
resource storageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, 'StorageQueueDataContributor')
  scope: storageAccount
  properties: {
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────

@description('Name of the Function App.')
output functionAppName string = functionApp.name

@description('Resource ID of the Function App.')
output functionAppId string = functionApp.id

@description('Default hostname of the Function App.')
output defaultHostName string = functionApp.properties.defaultHostName

@description('Principal ID of the Function App system-assigned managed identity.')
output principalId string = functionApp.identity.principalId
