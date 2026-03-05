using '../main.bicep'

param environmentName = 'prod'

param tags = {
  environment: 'prod'
  project: 'forms-to-fabric'
  managedBy: 'bicep'
}

// Option A: Create a new Fabric capacity for prod
// param fabricCapacityName = 'forms-to-fabric-prod'
// param fabricAdminMembers = ['your-admin@yourdomain.com']

// Option B: Use an existing capacity (recommended for prod)
param existingFabricCapacityId = ''  // Set to your capacity resource ID
