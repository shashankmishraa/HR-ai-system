# ============================================
# run_demo.ps1  —  Top-5 view + RL decision + single hire save
# Requires your Flask API running locally (http://127.0.0.1:5000)
# Saves ONLY hired rows into C:\Task_Aiml_Intern\data\hired_candidates.csv (overwrite each run)
# ============================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---- Config ----
$ApiBase   = "http://127.0.0.1:5000"
$DataDir   = "C:\Task_Aiml_Intern\data"
$JdCsvPath = Join-Path $DataDir "sample_jds.csv"
$OutCsv    = Join-Path $DataDir "hired_candidates.csv"

# ---- Helpers ----

function Test-ApiHealth {
    try {
        $h = Invoke-RestMethod -Uri "$ApiBase/health" -Method GET -TimeoutSec 10
        Write-Host "`n===== API HEALTH CHECK =====" -ForegroundColor Cyan
        $h | ConvertTo-Json -Depth 5
        return $true
    } catch {
        Write-Host "API not reachable at $ApiBase  ->  $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Get-JdIds {
    if (-not (Test-Path $JdCsvPath)) {
        throw "JD CSV not found at $JdCsvPath"
    }
    $rows = Import-Csv $JdCsvPath

    $col =
        if ($rows[0].PSObject.Properties.Name -contains 'id')     { 'id' }
        elseif ($rows[0].PSObject.Properties.Name -contains 'jd_id') { 'jd_id' }
        else { throw "JD CSV must contain 'id' or 'jd_id' column." }

    $rows | ForEach-Object { $_.$col } | Where-Object { $_ } | Select-Object -Unique
}

function Get-TopCandidates {
    param(
        [Parameter(Mandatory)] [string] $Jd,
        [int] $TopN = 5
    )
    try {
        $raw = Invoke-RestMethod -Uri "$ApiBase/top_candidates?jd_id=$Jd&top_n=20" -Method GET
    } catch {
        Write-Host "Error fetching data for $Jd -> $($_.Exception.Message)" -ForegroundColor Red
        return @()
    }
    if (-not $raw) { return @() }

    $sorted = $raw | Sort-Object `
        @{Expression = 'location_match'; Descending = $true}, `
        @{Expression = 'score';           Descending = $true}, `
        @{Expression = 'skill_overlap';   Descending = $true}

    $sorted | Select-Object -First $TopN
}

function Get-DecideDetails {
    param(
        [Parameter(Mandatory)] [string] $CvId,
        [Parameter(Mandatory)] [string] $JdId
    )
    $payload = @{ cv_id = $CvId; jd_id = $JdId } | ConvertTo-Json -Compress
    try {
        Invoke-RestMethod -Uri "$ApiBase/decide" -Method POST -ContentType "application/json" -Body $payload
    } catch {
        $null
    }
}

function Show-Top5 {
    param(
        [Parameter(Mandatory)] [string] $Jd,
        [Parameter(Mandatory)] [array]  $Top5
    )
    Write-Host "`n===== TOP 5 CANDIDATES for $Jd =====" -ForegroundColor Yellow
    $i = 1
    foreach ($c in $Top5) {
        Write-Host ("{0}) {1} | Score: {2:N3} | Skills: {3} | LocationMatch: {4}" -f `
            $i, $c.cv_id, [double]$c.score, [int]$c.skill_overlap, [bool]$c.location_match)
        
        # Get RL decision
        $eval = Get-DecideDetails -CvId $c.cv_id -JdId $c.jd_id
        if ($eval -and $eval.rl_action) {
            $color = "White"
            switch ($eval.rl_action) {
                "HIRE"        { $color = "Green" }
                "REJECT"      { $color = "Red" }
                "ASSIGN_TASK" { $color = "Blue" }
                "HOLD"        { $color = "Yellow" }
            }
            Write-Host ("    RL Decision: {0} (Source: {1})" -f $eval.rl_action, $eval.decision_source) -ForegroundColor $color
        }

        if ($c.PSObject.Properties.Name -contains 'rank') {
            Write-Host ("    Rank: {0}" -f [int]$c.rank)
        }
        if ($c.PSObject.Properties.Name -contains 'resume_snippet' -and $c.resume_snippet) {
            Write-Host ("    Snippet: {0}" -f ($c.resume_snippet -replace "`r?`n",' ')).Substring(0, [Math]::Min(160, ($c.resume_snippet).Length))
        }
        $i++
    }
}

function Select-Hire {
    param([Parameter(Mandatory)] [array] $Top5)
    if (-not $Top5 -or $Top5.Count -eq 0) { return $null }

    # Try RL-based selection first
    foreach ($c in $Top5) {
        $eval = Get-DecideDetails -CvId $c.cv_id -JdId $c.jd_id
        if ($eval -and $eval.rl_action -eq "HIRE") {
            $c | Add-Member -NotePropertyName rl_action -NotePropertyValue $eval.rl_action -Force
            $c | Add-Member -NotePropertyName decision_source -NotePropertyValue $eval.decision_source -Force
            return $c
        }
    }

    # Fallback: best by sort
    $best = $Top5 | Sort-Object `
        @{Expression = 'location_match'; Descending = $true}, `
        @{Expression = 'score';           Descending = $true}, `
        @{Expression = 'skill_overlap';   Descending = $true} `
    | Select-Object -First 1

    # Attach RL data for fallback hire
    $evalBest = Get-DecideDetails -CvId $best.cv_id -JdId $best.jd_id
    if ($evalBest) {
        $best | Add-Member -NotePropertyName rl_action -NotePropertyValue $evalBest.rl_action -Force
        $best | Add-Member -NotePropertyName decision_source -NotePropertyValue $evalBest.decision_source -Force
    } else {
        # Ensure properties exist even if no API data
        $best | Add-Member -NotePropertyName rl_action -NotePropertyValue $null -Force
        $best | Add-Member -NotePropertyName decision_source -NotePropertyValue $null -Force
    }

    return $best
}


function To-FlattenedRow {
    param(
        [Parameter(Mandatory)] $TopRow
    )
    [PSCustomObject]@{
        jd_id           = $TopRow.jd_id
        jd_title        = $TopRow.jd_title
        cv_id           = $TopRow.cv_id
        cv_name         = $TopRow.cv_name
        score           = [double]$TopRow.score
        skill_overlap   = [int]$TopRow.skill_overlap
        location_match  = [bool]$TopRow.location_match
        rl_action       = if ($TopRow.PSObject.Properties.Name -contains 'rl_action') { $TopRow.rl_action } else { $null }
        decision_source = if ($TopRow.PSObject.Properties.Name -contains 'decision_source') { $TopRow.decision_source } else { $null }
        timestamp       = (Get-Date).ToString("s")
    }
}

function Process-OneJD {
    param([Parameter(Mandatory)] [string] $Jd)

    $top5 = Get-TopCandidates -Jd $Jd -TopN 5
    if (-not $top5 -or $top5.Count -eq 0) {
        Write-Host "No candidates found for $Jd" -ForegroundColor Yellow
        return $null
    }

    Show-Top5 -Jd $Jd -Top5 $top5

    $hire = Select-Hire -Top5 $top5
    if ($null -eq $hire) {
        Write-Host "No hire selected for $Jd" -ForegroundColor Yellow
        return $null
    }

    Write-Host "`n===== SELECTED HIRE for $Jd =====" -ForegroundColor Green
    $color = if ($hire.rl_action -eq "HIRE") { "Green" } else { "White" }
    Write-Host ("[HIRE] {0} | Score: {1:N3} | Skills: {2} | LocationMatch: {3}" -f `
        $hire.cv_id, [double]$hire.score, [int]$hire.skill_overlap, [bool]$hire.location_match) -ForegroundColor $color
    if ($hire.rl_action) {
        Write-Host ("    RL Decision: {0} (Source: {1})" -f $hire.rl_action, $hire.decision_source) -ForegroundColor $color
    }

    To-FlattenedRow -TopRow $hire
}

# -------------------------
# Main
# -------------------------

if (-not (Test-ApiHealth)) { exit 1 }

$jdIds = @()
try {
    $jdIds = Get-JdIds
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

$choice = Read-Host "Do you want to run for All JDs or One JD? (Enter 'all' or 'one')"
$choice = $choice.ToLower().Trim()

$hiredRows = @()

switch ($choice) {
    'one' {
        $jd = Read-Host "Enter JD ID (e.g., JD_1, JD_2)"
        if (-not $jd) { Write-Host "No JD provided." -ForegroundColor Red; exit 1 }
        $row = Process-OneJD -Jd $jd
        if ($row) { $hiredRows += $row }
    }
    'all' {
        foreach ($jd in $jdIds) {
            $row = Process-OneJD -Jd $jd
            if ($row) { $hiredRows += $row }
        }
    }
    default {
        Write-Host "Invalid choice. Please enter 'all' or 'one'." -ForegroundColor Red
        exit 1
    }
}

if ($hiredRows.Count -gt 0) {
    $hiredRows | Export-Csv -Path $OutCsv -NoTypeInformation
    Write-Host "`n===== SAVED $(($hiredRows | Measure-Object).Count) HIRED ROW(S) to $OutCsv =====" -ForegroundColor Green
} else {
    Write-Host "`n===== NO HIRES SELECTED. NOTHING SAVED =====" -ForegroundColor Yellow
}
