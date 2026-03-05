// ──────────────────────────────────────────────
// Function App module – Linux Consumption (Python 3.10)
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
  name: 'func-forms-${environmentName}'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.10'
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
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: 'func-forms-${environmentName}'
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
