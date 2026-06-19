$ip = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -ne "127.0.0.1" -and
        $_.IPAddress -notlike "169.*"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress

$apiUrl = "http://$ip:8000/api/v1"

Write-Host ""
Write-Host "Detected Laptop IP: $ip" -ForegroundColor Green
Write-Host "API URL: $apiUrl" -ForegroundColor Green
Write-Host ""

flutter run --dart-define="API_BASE_URL=$apiUrl"