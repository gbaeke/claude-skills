// One Container App on the existing infrastructure (main.bicep): only this resource changes on a deploy.
// scripts/azure-deploy.sh builds and pushes the image, then deploys this file. Another app or a worker in the same
// environment is another deployment of this file with its own name and image.

@description('Region (the infrastructure\'s).')
param location string = resourceGroup().location

@description('The Container App\'s name; also its host name.')
param name string = '{{app}}'

@description('Image to run: <registry>.azurecr.io/{{app}}:<tag>.')
param image string
{{#auth}}

@description('WorkOS client id: the app\'s own sign-in (AuthKit). Empty: no sign-in.')
param workosClientId string = ''

@secure()
param workosApiKey string = ''

@secure()
@description('Encrypts the session cookie (SESSION_SECRET); changing it signs everyone out.')
param sessionSecret string = ''

@description('Comma separated emails the app lets in (ALLOWED_USERS). Empty: everyone WorkOS lets in.')
param allowedUsers string = ''
{{/auth}}

@description('Ingress IP rules (ipSecurityRestrictions). Empty: open to every address.')
param ipRules array = []

// the same names main.bicep gives its resources
var suffix = take(uniqueString(resourceGroup().id), 6)

resource env 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: 'cae-${suffix}'
}

resource acr 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: 'acr${suffix}'
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' existing = {
  name: 'id-${suffix}'
}
{{#db}}

resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' existing = {
  name: 'pg-${suffix}'
}

// no password: the app signs in with a token for its managed identity (db.py), so this is not a secret
var databaseUrl = 'postgresql://${identity.name}@${pg.properties.fullyQualifiedDomainName}:5432/{{pkg}}?sslmode=require'
{{/db}}
{{#auth}}

var withWorkos = !empty(workosClientId)
// PUBLIC_URL: behind the ingress the app sees http, and builds the callback URL from this instead
var workosEnv = withWorkos ? concat([
  { name: 'WORKOS_CLIENT_ID', value: workosClientId }
  { name: 'WORKOS_API_KEY', secretRef: 'workos-api-key' }
  { name: 'SESSION_SECRET', secretRef: 'session-secret' }
  { name: 'PUBLIC_URL', value: 'https://${name}.${env.properties.defaultDomain}' }
], empty(allowedUsers) ? [] : [{ name: 'ALLOWED_USERS', value: allowedUsers }]) : []
{{/auth}}

var secrets = concat(
{{#auth}}
  withWorkos ? [{ name: 'workos-api-key', value: workosApiKey }, { name: 'session-secret', value: sessionSecret }] : [],
{{/auth}}
  []
)
var appEnv = concat(
  [{ name: 'LOG_JSON', value: 'true' }],
{{#db}}
  [
    { name: 'DATABASE_URL', value: databaseUrl }
    { name: 'DATABASE_ENTRA_AUTH', value: 'true' }
    { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId } // which identity DefaultAzureCredential uses
  ],
{{/db}}
{{#auth}}
  workosEnv,
{{/auth}}
  []
)

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    environmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        ipSecurityRestrictions: ipRules
      }
      registries: [{ server: acr.properties.loginServer, identity: identity.id }]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'app'
          image: image
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: appEnv
          // traffic only once the app answers: startup runs the migrations
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 2
              periodSeconds: 5
              failureThreshold: 12
            }
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              periodSeconds: 15
              failureThreshold: 3
            }
          ]
        }
      ]
      // migrations run at startup under a lock, so more replicas are safe for them; raise maxReplicas once nothing
      // else lives in process memory (queues, caches, progress)
      scale: { minReplicas: 0, maxReplicas: 1 }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
