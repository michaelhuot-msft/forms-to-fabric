using '../main.bicep'

param environmentName = 'dev'

param tags = {
  environment: 'dev'
  project: 'forms-to-fabric'
  managedBy: 'bicep'
}
