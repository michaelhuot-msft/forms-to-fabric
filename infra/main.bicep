targetScope = 'resourceGroup'

// ──────────────────────────────────────────────
// Parameters
// ──────────────────────────────────────────────

@description('Name of the environment (e.g. dev, staging, prod). Used in resource naming.')
param environmentName string

@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Tags to apply to every resource.')
param tags object = {}

@description('Microsoft Fabric OneLake endpoint URL.')
param onelakeEndpoint string = 'https://onelake.dfs.fabric.microsoft.com'

@description('Path inside the storage container where the form-registry configuration is stored.')
param formRegistryPath string = 'form-registry/registry.json'

// ──────────────────────────────────────────────
// Variables
// ──────────────────────────────────────────────

var keyVaultName = 'kv-forms-${environmentName}'

// ──────────────────────────────────────────────
// Modules
// ──────────────────────────────────────────────

module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsights'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

module functionApp 'modules/function-app.bicep' = {
  name: 'functionApp'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    storageAccountName: storage.outputs.storageAccountName
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
    appInsightsConnectionString: appInsights.outputs.connectionString
    keyVaultName: keyVaultName
    onelakeEndpoint: onelakeEndpoint
    formRegistryPath: formRegistryPath
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    functionAppPrincipalId: functionApp.outputs.principalId
    logAnalyticsWorkspaceId: appInsights.outputs.logAnalyticsWorkspaceId
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────

@description('Name of the deployed Function App.')
output functionAppName string = functionApp.outputs.functionAppName

@description('Default hostname of the Function App.')
output functionAppHostName string = functionApp.outputs.defaultHostName

@description('Resource ID of the Key Vault.')
output keyVaultId string = keyVault.outputs.keyVaultId

@description('Name of the Key Vault.')
output keyVaultName string = keyVault.outputs.keyVaultName

@description('Name of the Storage Account.')
output storageAccountName string = storage.outputs.storageAccountName

@description('Resource ID of Application Insights.')
output appInsightsId string = appInsights.outputs.appInsightsId
