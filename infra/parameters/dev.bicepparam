using '../main.bicep'

param environmentName = 'dev'

param tags = {
  environment: 'dev'
  project: 'forms-to-fabric'
  managedBy: 'bicep'
}

param fabricAdminMembers = ['your-admin@yourdomain.com']
