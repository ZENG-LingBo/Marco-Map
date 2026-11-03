# Adds an rclone remote called "r2" for the project's Cloudflare R2 account.
#
#   powershell -File scripts\setup_rclone_r2.ps1 -AccountId <Cloudflare account id>
#
# Create the key first: Cloudflare dashboard > R2 > Manage API tokens > Create API token, permission
# "Object Read & Write", limited to the one bucket. The secret is shown once. This script asks for the pair
# (the secret is not echoed) and hands it to rclone, so it is not typed into a chat or kept in shell history.
# Delete the token in the dashboard when the upload is done.
param(
    [Parameter(Mandatory)][string]$AccountId,  # dashboard > R2 > Overview, or `wrangler whoami`
    [string]$Bucket = 'mapping-tartary-tiles'
)

$rclone = (Get-Command rclone -ErrorAction SilentlyContinue).Source
if (-not $rclone) {
    $rclone = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter rclone.exe -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if (-not $rclone) { throw 'rclone not found; install it with: winget install Rclone.Rclone' }

$id = Read-Host 'R2 Access Key ID'
$secret = Read-Host 'R2 Secret Access Key' -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret))

& $rclone config create r2 s3 provider=Cloudflare "access_key_id=$id" "secret_access_key=$plain" `
    "endpoint=https://$AccountId.r2.cloudflarestorage.com" acl=private no_check_bucket=true | Out-Null
$plain = $null

& $rclone lsd "r2:$Bucket"
if ($LASTEXITCODE -eq 0) { Write-Host "rclone remote r2 works for bucket $Bucket" -ForegroundColor Green }
else { Write-Host 'rclone could not reach the bucket; check the key, its bucket and its permission' -ForegroundColor Red }
