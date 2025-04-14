# install.ps1

# Define where to install the repo
$installDir = "C:\monad"
$repoUrl = "https://github.com/mothDAbug/Monad.git"
$zipUrl = "https://github.com/mothDAbug/Monad/archive/refs/heads/main.zip"  # The URL for downloading as a ZIP

# Create install directory if it doesn't exist
if (-Not (Test-Path -Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# Check if Git is installed
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Output "Git is installed. Cloning the repository..."
    # Clone the repo using Git
    $repoClonePath = "$installDir\monad-main"
    git clone $repoUrl $repoClonePath
} else {
    Write-Warning "Git is not installed. Falling back to downloading ZIP..."
    # Download the ZIP file of the repo and extract it
    $zipFile = "$env:TEMP\monad.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile
    Expand-Archive -Path $zipFile -DestinationPath $installDir -Force
    Remove-Item -Path $zipFile
    $repoClonePath = "$installDir\Monad-main"
}

# Create a .bat wrapper to run launcher.py from the cloned/extracted repo
$batContent = "@echo off`npython `"$repoClonePath\launcher.py`" %*"
$batPath = "$installDir\monad.bat"
$batContent | Set-Content -Path $batPath -Encoding ASCII

# Add the folder to the PATH (if not already present)
if (-not ($env:Path -split ";" | Where-Object { $_ -eq $installDir })) {
    [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$installDir", "User")
    Write-Output "Added $installDir to PATH"
} else {
    Write-Output "$installDir already in PATH"
}

# Final message after installation is complete
Write-Output "`n✅ Monad is now installed."
Write-Output "You can now use the command 'monad' to use our features."
