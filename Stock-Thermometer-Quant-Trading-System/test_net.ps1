try {
    $r = Invoke-WebRequest -Uri "https://push2.eastmoney.com/api/qt/clist/get" -TimeoutSec 10 -UseBasicParsing
    Write-Host "OK: $($r.StatusCode)"
} catch {
    Write-Host "FAIL: $($_.Exception.Message)"
}
