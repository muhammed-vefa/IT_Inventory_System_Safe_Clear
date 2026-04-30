$filePath = "frontend\UI_controller.js"
$lines = Get-Content $filePath
$secondAppLine = -1
for ($i = 1; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "appData = \{") {
        $secondAppLine = $i
        # We want the 'var app =' line which is usually just before or part of the corruption
        break
    }
}

if ($secondAppLine -gt 0) {
    # The corruption is at line 3929 (index 3928)
    # var app line was at 3929 (index 3928)
    $newLines = @("var app = window.app || {};")
    for ($i = 3929; $i -lt $lines.Count; $i++) {
        $newLines += $lines[$i]
    }
    [System.IO.File]::WriteAllLines($filePath, $newLines, [System.Text.Encoding]::UTF8)
    Write-Output "Restored from line 3930"
} else {
    Write-Output "Could not find second appData"
}
