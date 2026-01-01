# Analyze EOP file structure
$path = "D:\dw11\piano\LyreAutoPlayer\赛马.eop"
$bytes = [System.IO.File]::ReadAllBytes($path)

Write-Host "=== EOP File Analysis ===" -ForegroundColor Cyan
Write-Host "File: $path"
Write-Host "Size: $($bytes.Length) bytes"
Write-Host ""

# First 64 bytes (header)
Write-Host "First 64 bytes (hex):" -ForegroundColor Yellow
for ($i = 0; $i -lt 64; $i += 16) {
    $line = ""
    $ascii = ""
    for ($j = 0; $j -lt 16 -and ($i + $j) -lt $bytes.Length; $j++) {
        $b = $bytes[$i + $j]
        $line += "{0:X2} " -f $b
        if ($b -ge 32 -and $b -le 126) {
            $ascii += [char]$b
        } else {
            $ascii += "."
        }
    }
    Write-Host ("{0:X4}: {1,-48} {2}" -f $i, $line, $ascii)
}

Write-Host ""
Write-Host "Byte frequency analysis (top 20):" -ForegroundColor Yellow
$freq = @{}
foreach ($b in $bytes) {
    if ($freq.ContainsKey($b)) {
        $freq[$b]++
    } else {
        $freq[$b] = 1
    }
}
$sorted = $freq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20
foreach ($item in $sorted) {
    $pct = [math]::Round(($item.Value / $bytes.Length) * 100, 2)
    Write-Host ("  0x{0:X2} ({1,3}): {2,5} times ({3}%)" -f $item.Key, $item.Key, $item.Value, $pct)
}

# Check for patterns
Write-Host ""
Write-Host "Pattern analysis:" -ForegroundColor Yellow

# Check if it could be compressed/encrypted
$entropy = 0
foreach ($item in $freq.GetEnumerator()) {
    $p = $item.Value / $bytes.Length
    if ($p -gt 0) {
        $entropy -= $p * [math]::Log($p, 2)
    }
}
Write-Host "  Entropy: $([math]::Round($entropy, 2)) bits/byte (max 8.0)"
if ($entropy -gt 7.5) {
    Write-Host "  -> Likely encrypted or compressed" -ForegroundColor Red
} elseif ($entropy -gt 6.0) {
    Write-Host "  -> Possibly compressed" -ForegroundColor Yellow
} else {
    Write-Host "  -> Likely uncompressed data" -ForegroundColor Green
}

# Look for common signatures
Write-Host ""
Write-Host "Signature search:" -ForegroundColor Yellow
$signatures = @{
    "MThd" = @(0x4D, 0x54, 0x68, 0x64)  # MIDI
    "PK" = @(0x50, 0x4B)                 # ZIP
    "Rar" = @(0x52, 0x61, 0x72)          # RAR
    "7z" = @(0x37, 0x7A, 0xBC, 0xAF)     # 7z
    "SQLite" = @(0x53, 0x51, 0x4C, 0x69) # SQLite
    "XML" = @(0x3C, 0x3F, 0x78, 0x6D)    # <?xml
}

foreach ($sig in $signatures.GetEnumerator()) {
    $found = $false
    for ($i = 0; $i -lt [math]::Min($bytes.Length, 1024); $i++) {
        $match = $true
        for ($j = 0; $j -lt $sig.Value.Length -and ($i + $j) -lt $bytes.Length; $j++) {
            if ($bytes[$i + $j] -ne $sig.Value[$j]) {
                $match = $false
                break
            }
        }
        if ($match) {
            Write-Host "  Found $($sig.Key) signature at offset $i"
            $found = $true
            break
        }
    }
}
