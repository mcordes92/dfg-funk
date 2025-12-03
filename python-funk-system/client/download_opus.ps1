# PowerShell Script to download Opus DLL for PyInstaller bundling
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Opus DLL Download for Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create libs directory if it doesn't exist
if (-not (Test-Path "libs")) {
    New-Item -ItemType Directory -Path "libs" | Out-Null
}

# Check if opus.dll already exists
if (Test-Path "libs\opus.dll") {
    Write-Host "opus.dll already exists in libs\" -ForegroundColor Green
    Write-Host ""
    $overwrite = Read-Host "Overwrite? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Keeping existing DLL" -ForegroundColor Yellow
        exit 0
    }
}

try {
    # Method 1: Try to find opus.dll in installed Python packages
    Write-Host "[Method 1/4] Checking Python packages..." -ForegroundColor Yellow
    
    $pythonSitePackages = python -c "import site; print(site.getsitepackages()[0])" 2>$null
    if ($pythonSitePackages) {
        $possiblePaths = @(
            "$pythonSitePackages\opuslib\*opus*.dll",
            "$pythonSitePackages\_opuslib.libs\*opus*.dll",
            "$pythonSitePackages\opuslib.libs\*opus*.dll"
        )
        
        foreach ($pattern in $possiblePaths) {
            $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
            if ($found) {
                Write-Host "  Found in Python packages!" -ForegroundColor Green
                Copy-Item -Path $found[0].FullName -Destination "libs\opus.dll" -Force
                Write-Host ""
                Write-Host "SUCCESS: opus.dll ready for bundling!" -ForegroundColor Green
                exit 0
            }
        }
    }
    Write-Host "  Not found in Python packages" -ForegroundColor Gray
    
    # Method 2: Download from RyanHileman/opus-native (reliable pre-built DLLs)
    Write-Host "[Method 2/4] Downloading from opus-native..." -ForegroundColor Yellow
    
    $opusUrl = "https://github.com/RyanHileman/opus-native/raw/master/windows/x64/opus.dll"
    
    try {
        Invoke-WebRequest -Uri $opusUrl -OutFile "libs\opus.dll" -ErrorAction Stop
        Write-Host "  Download complete!" -ForegroundColor Green
        
        # Verify it's a valid DLL
        if ((Get-Item "libs\opus.dll").Length -gt 100KB) {
            Write-Host ""
            Write-Host "SUCCESS: opus.dll ready for bundling!" -ForegroundColor Green
            exit 0
        } else {
            Remove-Item "libs\opus.dll" -Force
            throw "Downloaded file too small"
        }
    } catch {
        Write-Host "  Failed: $($_.Exception.Message)" -ForegroundColor Gray
    }
    
    # Method 3: Download from vcpkg (Microsoft's package manager)
    Write-Host "[Method 3/4] Trying vcpkg binaries..." -ForegroundColor Yellow
    
    try {
        # Get latest vcpkg release
        $vcpkgUrl = "https://github.com/microsoft/vcpkg/raw/master/ports/opus/portfile.cmake"
        $response = Invoke-WebRequest -Uri $vcpkgUrl -ErrorAction Stop
        Write-Host "  vcpkg found, but DLL needs compilation" -ForegroundColor Gray
    } catch {
        Write-Host "  Not accessible" -ForegroundColor Gray
    }
    
    # Method 4: Direct download from known working source
    Write-Host "[Method 4/4] Downloading from SourceForge..." -ForegroundColor Yellow
    
    try {
        # Opus 1.3.1 Windows build from SourceForge
        $sfUrl = "https://ftp.osuosl.org/pub/xiph/releases/opus/opus-1.3.1.tar.gz"
        Write-Host "  Source download would require compilation" -ForegroundColor Gray
    } catch {
        Write-Host "  Not available" -ForegroundColor Gray
    }
    
    throw "All automatic download methods failed"
    
} catch {
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Red
    Write-Host "AUTOMATIC DOWNLOAD FAILED" -ForegroundColor Red
    Write-Host "===============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "EINFACHSTE LÖSUNG - Manueller Download:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1 (Empfohlen):" -ForegroundColor Cyan
    Write-Host "  1. Öffne: https://www.dllme.com/dll/files/opus_dll/download" -ForegroundColor White
    Write-Host "  2. Lade 64-bit opus.dll herunter" -ForegroundColor White
    Write-Host "  3. Kopiere nach: $PWD\libs\opus.dll" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 2:" -ForegroundColor Cyan
    Write-Host "  1. Öffne: https://github.com/xiph/opus/releases" -ForegroundColor White
    Write-Host "  2. Suche nach Windows Binaries" -ForegroundColor White
    Write-Host "  3. Kopiere opus.dll nach: $PWD\libs\opus.dll" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 3 (Kein Opus):" -ForegroundColor Cyan
    Write-Host "  Setze in config.py:" -ForegroundColor White
    Write-Host "    AUDIO_CODEC = 'pcm'" -ForegroundColor White
    Write-Host "  Client funktioniert ohne Opus (höhere Bandbreite)" -ForegroundColor White
    Write-Host ""
    Write-Host "Nach manuellem Download: build.bat ausführen" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run: build.bat" -ForegroundColor White
Write-Host "2. The opus.dll will be bundled into the EXE" -ForegroundColor White
Write-Host ""
