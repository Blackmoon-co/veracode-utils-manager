# Instalar el módulo de Veracode si no está instalado
if (-not (Get-Module -ListAvailable -Name VeracodeAPI)) {
    Install-Module -Name VeracodeAPI -Force -Scope CurrentUser
}

# Importar el módulo
Import-Module VeracodeAPI

# Definir las credenciales
$ApiId = "b0a30b5cb828ffe71aabb51f953173b0"
$ApiKey = "2e517602c74af7107f3b754975a17c5c20166b17d3a4eb4cfa3cd09002ea46ec6b454337a8bcca53a17ed49f5e1b1e2610d97bd48134ad9fc33b26d177907155"

# Validar la clave hexadecimal
Write-Host "Longitud de la clave: $($ApiKey.Length)"
if ($ApiKey.Length % 2 -ne 0) {
    Write-Host "ERROR: La clave no tiene longitud par."
    exit
}
if ($ApiKey -match '[^0-9a-fA-F]') {
    Write-Host "ERROR: La clave contiene caracteres no hexadecimales."
    exit
}

# Configuración de la petición
$method = "GET"
$apiHost = "api.veracode.com"
$path = "/api/authn/v2/teams"

# Generar timestamp y nonce
$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$nonce = ([guid]::NewGuid().ToString() -replace "-", "")

# Crear la cadena a firmar
$dataToSign = "$timestamp|$nonce|$method|$path|$apiHost|"

# Función para convertir hexadecimal a bytes
function Convert-HexToBytes {
    param([string]$hex)
    $bytes = New-Object byte[] ($hex.Length / 2)
    for ($i = 0; $i -lt $hex.Length; $i += 2) {
        $bytes[$i/2] = [Convert]::ToByte($hex.Substring($i, 2), 16)
    }
    return $bytes
}

# Crear la firma HMAC
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = Convert-HexToBytes $ApiKey
$signatureBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($dataToSign))
$signature = [Convert]::ToBase64String($signatureBytes)

# Crear el header de autorización
$authHeader = "VERACODE-HMAC-SHA-256 id=$ApiId,ts=$timestamp,nonce=$nonce,sig=$signature"

# Construir la URL
$uri = "https://$apiHost$path"

try {
    # Realizar la petición
    $response = Invoke-RestMethod -Uri $uri -Method $method -Headers @{
        "Authorization" = $authHeader
        "Content-Type" = "application/json"
    }
    
    # Mostrar los resultados
    Write-Host "Equipos encontrados:"
    $response | ConvertTo-Json
}
catch {
    Write-Host "Error: $_"
} 