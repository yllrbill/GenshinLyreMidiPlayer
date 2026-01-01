# Analyze EOP file structure
$path = "D:\dw11\.claude\state\sample.eop"
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

# Calculate entropy
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
    Write-Host "  -> Likely uncompressed structured data" -ForegroundColor Green
}

# Look for common signatures
Write-Host ""
Write-Host "Signature search:" -ForegroundColor Yellow
$signatures = @{
    "MIDI (MThd)" = @(0x4D, 0x54, 0x68, 0x64)
    "ZIP (PK)" = @(0x50, 0x4B, 0x03, 0x04)
    "RAR" = @(0x52, 0x61, 0x72, 0x21)
    "7z" = @(0x37, 0x7A, 0xBC, 0xAF)
    "SQLite" = @(0x53, 0x51, 0x4C, 0x69)
    "XML (<?xml)" = @(0x3C, 0x3F, 0x78, 0x6D)
    "JSON ({)" = @(0x7B)
    "BOM UTF-8" = @(0xEF, 0xBB, 0xBF)
    "BOM UTF-16 LE" = @(0xFF, 0xFE)
    "ZLIB" = @(0x78, 0x9C)
}

foreach ($sig in $signatures.GetEnumerator()) {
    for ($i = 0; $i -lt [math]::Min($bytes.Length, 256); $i++) {
        $match = $true
        for ($j = 0; $j -lt $sig.Value.Length -and ($i + $j) -lt $bytes.Length; $j++) {
            if ($bytes[$i + $j] -ne $sig.Value[$j]) {
                $match = $false
                break
            }
        }
        if ($match) {
            Write-Host "  Found $($sig.Key) at offset $i" -ForegroundColor Green
            break
        }
    }
}

# Analyze repeating patterns
Write-Host ""
Write-Host "Structure hints:" -ForegroundColor Yellow
$firstFour = "{0:X2} {1:X2} {2:X2} {3:X2}" -f $bytes[0], $bytes[1], $bytes[2], $bytes[3]
Write-Host "  Magic/Header: $firstFour"

# Check if data looks like note events
$noteRange = 0
foreach ($b in $bytes) {
    if ($b -ge 0x30 -and $b -le 0x7F) { $noteRange++ }
}
$noteRangePct = [math]::Round(($noteRange / $bytes.Length) * 100, 1)
Write-Host "  Bytes in MIDI note range (0x30-0x7F): $noteRange ($noteRangePct%)"
