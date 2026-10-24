param([Parameter(Mandatory = $true)][string]$Uri)

# ---------------- Configuration (edit per workstation) ----------------
$OdooBase     = 'http://192.168.100.100:8069'
$ProjectsRoot = 'C:\exocad\DentalLabProjects'
$TemplateFile = Join-Path $PSScriptRoot 'template.dentalProject'
$ExocadExe    = 'D:\Softwares\3D\ExoCad\exocad-DentalCAD3.2-2024-02-24\exocad-DentalCAD3.2-2024-02-24\DentalCADApp\bin\DentalCADApp.exe'   # full path to the exocad executable; empty = use the file association
# -----------------------------------------------------------------------

Add-Type -AssemblyName System.Web
Add-Type -AssemblyName PresentationFramework
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Show-Error([string]$msg) {
    [System.Windows.MessageBox]::Show($msg, 'Dental Lab - exocad', 'OK', 'Error') | Out-Null
}
function Get-SafeName([string]$s) { ($s -replace '[\\/:*?"<>|]', '_').Trim() }
function Esc([string]$s) { [System.Security.SecurityElement]::Escape($s) }

try {
    $q = [System.Web.HttpUtility]::ParseQueryString(([System.Uri]$Uri).Query)
    $orderId = [int]$q['order']
    $token = $q['token']
    if ($token -notmatch '^\d+\.\d+\.[0-9a-f]{64}$') { throw 'Invalid token.' }

    $o = Invoke-RestMethod -Uri "$OdooBase/dental_lab/exocad/order/$orderId`?token=$token" -Method Get

    $safeName = Get-SafeName "$($o.reference)_$($o.patient_name)"
    $dir = Join-Path $ProjectsRoot $safeName
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    # Scans / attachments
    foreach ($a in $o.attachments) {
        $target = Join-Path $dir (Get-SafeName (Split-Path $a.name -Leaf))
        Invoke-WebRequest -Uri ($OdooBase + $a.url) -OutFile $target -UseBasicParsing
    }

    # Raw order data kept next to the project
    $o | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $dir 'order.json') -Encoding UTF8

    # Project file from the template (never overwrite existing work)
    $ext = [System.IO.Path]::GetExtension($TemplateFile)
    $projectFile = Join-Path $dir ($safeName + $ext)
    if (-not (Test-Path $projectFile)) {
        $map = @{
            'reference'    = $o.reference
            'form_number'  = $o.form_number
            'dentist'      = $o.dentist
            'patient_name' = $o.patient_name
            'technician'   = $o.technician
            'shade'        = $o.shade
            'order_date'   = $o.order_date
            'due_date'     = $o.due_date
            'priority'     = $o.priority
            'notes'        = $o.notes
            'teeth'        = ($o.teeth -join ',')
        }
        $xml = Get-Content $TemplateFile -Raw -Encoding UTF8
        foreach ($k in $map.Keys) { $xml = $xml.Replace("{{$k}}", (Esc ([string]$map[$k]))) }
        Set-Content -Path $projectFile -Value $xml -Encoding UTF8
    }

    if ($ExocadExe) { Start-Process -FilePath $ExocadExe -ArgumentList "`"$projectFile`"" }
    else            { Start-Process -FilePath $projectFile }
}
catch {
    Show-Error "Could not open exocad project:`n$($_.Exception.Message)"
}