using '../main.bicep'

param environmentName = 'prod'

param tags = {
  environment: 'prod'
  project: 'forms-to-fabric'
  managedBy: 'bicep'
}

param fabricAdminMembers = ['your-admin@yourdomain.com']
