param(
    [Parameter(Mandatory = $true)][string]$ImagePath,
    [Parameter(Mandatory = $true)][string]$OutPath,
    [string]$Lang = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"

function Step($name, [scriptblock]$body) {
    try {
        $r = & $body
        [Console]::Error.WriteLine("OK   " + $name)
        return $r
    } catch {
        [Console]::Error.WriteLine("FAIL " + $name + " : " + $_.Exception.Message)
        if ($_.Exception.InnerException) {
            [Console]::Error.WriteLine("      inner: " + $_.Exception.InnerException.Message)
        }
        throw
    }
}

try {
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
    Write-Output ("Engine " + $engine.RecognizerLanguage.LanguageTag + " MaxDim=" + [Windows.Media.Ocr.OcrEngine]::MaxImageDimension)

    $file = Step "GetFile" { Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile]) }
    $stream = Step "OpenAsync" { Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream]) }
    $decoder = Step "CreateDecoder" { Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]) }
    Write-Output ("Size " + $decoder.PixelWidth + "x" + $decoder.PixelHeight)
    $bitmap = Step "SoftwareBitmap" {
        Await ($decoder.GetSoftwareBitmapAsync(
                [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
                [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)) ([Windows.Graphics.Imaging.SoftwareBitmap])
    }
    $result = Step "Recognize" { Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult]) }

    $items = New-Object System.Collections.ArrayList
    foreach ($line in $result.Lines) {
        if ($line.Words.Count -eq 0) { continue }
        $minX = [double]::MaxValue; $minY = [double]::MaxValue
        $maxX = 0.0; $maxY = 0.0
        foreach ($w in $line.Words) {
            $r = $w.BoundingRect
            if ($r.X -lt $minX) { $minX = $r.X }
            if ($r.Y -lt $minY) { $minY = $r.Y }
            if (($r.X + $r.Width) -gt $maxX) { $maxX = $r.X + $r.Width }
            if (($r.Y + $r.Height) -gt $maxY) { $maxY = $r.Y + $r.Height }
        }
        $null = $items.Add([pscustomobject]@{
                text = $line.Text
                x    = [math]::Round($minX, 1)
                y    = [math]::Round($minY, 1)
                w    = [math]::Round($maxX - $minX, 1)
                h    = [math]::Round($maxY - $minY, 1)
            })
    }

    $json = $items | ConvertTo-Json -Depth 4 -Compress
    [System.IO.File]::WriteAllText($OutPath, $json, (New-Object System.Text.UTF8Encoding($false)))
    Write-Output ("Lines=" + $items.Count + " -> " + $OutPath)
} catch {
    Write-Output ("FATAL: " + $_.Exception.ToString())
    exit 1
}
