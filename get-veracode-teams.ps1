function Get-VeracodeTeams {
    param (
        [Parameter(Mandatory=$true)]
        [string]$ApiId,
        
        [Parameter(Mandatory=$true)]
        [string]$ApiKey
    )

    $method = "GET"
    $apiHost = "api.veracode.com"
    $path = "/api/authn/v2/teams"
    
    # Obtener el header de autorización
    $authHeader = Get-HmacAuthorizationHeader -ApiId $ApiId -ApiKey $ApiKey -HttpMethod $method -RequestPath $path -Host $apiHost
    
    # Construir la URL
    $uri = "https://$apiHost$path"
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method $method -Headers @{
            "Authorization" = $authHeader
            "Content-Type" = "application/json"
        }
        return $response
    }
    catch {
        Write-Error "Error al obtener teams: $_"
        return $null
    }
}

# Ejemplo de uso:
# Get-VeracodeTeams -ApiId "tu_api_id" -ApiKey "tu_api_key" 