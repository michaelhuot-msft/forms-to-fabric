using '../main.bicep'

param environmentName = 'dev'

param tags = {
  environment: 'dev'
  project: 'forms-to-fabric'
  managedBy: 'bicep'
}

// Option A: Create a new Fabric capacity for dev
param fabricCapacityName = 'formstofabricdev'
param fabricAdminMembers = ['your-admin@yourdomain.com']

// Option B: Use an existing capacity (uncomment and set, remove Option A params)
// param existingFabricCapacityId = '/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Fabric/capacities/<name>'
