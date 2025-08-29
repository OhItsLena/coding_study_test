$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "mitmdump"
$psi.Arguments = "-s C:\proxy.py"
$psi.WindowStyle = "Hidden"
$psi.CreateNoWindow = $true
[System.Diagnostics.Process]::Start($psi)