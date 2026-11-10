param(
    [Parameter(Mandatory = $true)][string]$Dir,
    [Parameter(Mandatory = $true)][string]$OutPath,
    [string]$Lang = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Lang))
if (-not $engine) { Write-Output "NO_ENGINE"; exit 2 }

$sw = [Diagnostics.Stopwatch]::StartNew()
$lines = New-Object System.Collections.ArrayList
$files = Get-ChildItem -Path $Dir -Filter '*.png' | Sort-Object Name
$i = 0
foreach ($f in $files) {
    $i++
    try {
        $sf = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)) ([Windows.Storage.StorageFile])
        $st = Await ($sf.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($st)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bm = Await ($dec.GetSoftwareBitmapAsync(
                [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
                [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $res = Await ($engine.RecognizeAsync($bm)) ([Windows.Media.Ocr.OcrResult])
        $arr = New-Object System.Collections.ArrayList
        foreach ($ln in $res.Lines) {
            if ($ln.Words.Count -eq 0) { continue }
            $minX = [double]::MaxValue; $minY = [double]::MaxValue
            $maxX = 0.0; $maxY = 0.0
            foreach ($w in $ln.Words) {
                $r = $w.BoundingRect
                if ($r.X -lt $minX) { $minX = $r.X }
                if ($r.Y -lt $minY) { $minY = $r.Y }
                if (($r.X + $r.Width) -gt $maxX) { $maxX = $r.X + $r.Width }
                if (($r.Y + $r.Height) -gt $maxY) { $maxY = $r.Y + $r.Height }
            }
            $null = $arr.Add([pscustomobject]@{
                    t = $ln.Text
                    x = [math]::Round($minX, 1); y = [math]::Round($minY, 1)
                    w = [math]::Round($maxX - $minX, 1); h = [math]::Round($maxY - $minY, 1)
                })
        }
        $null = $lines.Add([pscustomobject]@{ id = $f.BaseName; lines = $arr })
        $st.Dispose()
    } catch {
        $null = $lines.Add([pscustomobject]@{ id = $f.BaseName; text = "!ERR " + $_.Exception.Message })
    }
    if ($i % 100 -eq 0) { [Console]::Error.WriteLine("$i / $($files.Count)  $([int]$sw.Elapsed.TotalSeconds)s") }
}

$json = $lines | ConvertTo-Json -Depth 3 -Compress
[System.IO.File]::WriteAllText($OutPath, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("OCR files=" + $lines.Count + " elapsed=" + [int]$sw.Elapsed.TotalSeconds + "s -> " + $OutPath)
