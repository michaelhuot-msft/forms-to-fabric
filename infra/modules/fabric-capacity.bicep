// ──────────────────────────────────────────────
// Fabric Capacity module
// ──────────────────────────────────────────────

@description('Name of the Fabric capacity.')
param capacityName string

@description('Azure region.')
param location string

@description('Fabric SKU.')
@allowed(['F2', 'F4', 'F8', 'F16', 'F32', 'F64'])
param skuName string = 'F2'

@description('Entra ID of the capacity admin(s).')
param adminMembers array

@description('Tags.')
param tags object = {}

resource fabricCapacity 'Microsoft.Fabric/capacities@2023-11-01' = {
  name: capacityName
  location: location
  sku: {
    name: skuName
    tier: 'Fabric'
  }
  properties: {
    administration: {
      members: adminMembers
    }
  }
  tags: tags
}

output capacityId string = fabricCapacity.id
output capacityName string = fabricCapacity.name
