try {
    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $langs = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages
    foreach ($l in $langs) { $l.LanguageTag }
    "COUNT=" + $langs.Count
} catch {
    "ERR: " + $_.Exception.Message
}
