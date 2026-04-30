$filePath = "frontend\UI_controller.js"
$content = Get-Content $filePath -Raw
$openBraces = ($content.ToCharArray() | Where-Object {$_ -eq '{'}).Count
$closeBraces = ($content.ToCharArray() | Where-Object {$_ -eq '}'}).Count
$openParens = ($content.ToCharArray() | Where-Object {$_ -eq '('}).Count
$closeParens = ($content.ToCharArray() | Where-Object {$_ -eq ')'}).Count
$openBrackets = ($content.ToCharArray() | Where-Object {$_ -eq '['}).Count
$closeBrackets = ($content.ToCharArray() | Where-Object {$_ -eq ']'}).Count

Write-Output "Braces: $openBraces / $closeBraces"
Write-Output "Parens: $openParens / $closeParens"
Write-Output "Brackets: $openBrackets / $closeBrackets"

if ($openBraces -ne $closeBraces) { Write-Output "ERROR: Braces mismatch" }
if ($openParens -ne $closeParens) { Write-Output "ERROR: Parens mismatch" }
if ($openBrackets -ne $closeBrackets) { Write-Output "ERROR: Brackets mismatch" }
