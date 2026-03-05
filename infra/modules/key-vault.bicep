// ──────────────────────────────────────────────
// Key Vault module – Standard SKU with soft-delete & purge protection
// ──────────────────────────────────────────────

@description('Name of the Key Vault. Must be globally unique.')
param keyVaultName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to resources.')
param tags object = {}

@description('Principal ID of the Function App managed identity for access policy.')
param functionAppPrincipalId string

@description('Resource ID of the Log Analytics workspace for diagnostic settings.')
param logAnalyticsWorkspaceId string

// ──────────────────────────────────────────────
// Key Vault
// ──────────────────────────────────────────────

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    enabledForTemplateDeployment: true
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: functionAppPrincipalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
    ]
  }
}

// ──────────────────────────────────────────────
// Function App Key Secret (placeholder — rotate after deploy)
// ──────────────────────────────────────────────

resource functionAppKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'function-app-key'
  properties: {
    value: 'PLACEHOLDER-ROTATE-AFTER-DEPLOY'
    contentType: 'Function App host key for Power Automate — rotate after first deploy'
    attributes: {
      enabled: true
    }
  }
}

// ──────────────────────────────────────────────
// Diagnostic settings
// ──────────────────────────────────────────────

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${keyVaultName}'
  scope: keyVault
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
      }
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// ──────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────

@description('Resource ID of the Key Vault.')
output keyVaultId string = keyVault.id

@description('Name of the Key Vault.')
output keyVaultName string = keyVault.name

@description('URI of the Key Vault.')
output keyVaultUri string = keyVault.properties.vaultUri

@description('URI of the function app key secret.')
output functionAppKeySecretUri string = functionAppKeySecret.properties.secretUri
