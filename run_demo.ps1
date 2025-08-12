# run_demo.ps1
# This script runs the candidate evaluation, shows top 5, selects 1 hire, saves only hired to CSV.

# Ensure we're in project root
Set-Location -Path "C:\Task_Aiml_Intern"

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Health check
Write-Host "`n--- Health Check ---" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method GET
    $health | Format-List
} catch {
    Write-Host "Flask API not running. Start it with: python -m app.api" -ForegroundColor Red
    exit
}

# Ask whether to run for all JDs or one
$mode = Read-Host "Do you want to run for All JDs or One JD? (Enter 'all' or 'one')"

# Load JD IDs from CSV
$jdFile = "C:\Task_Aiml_Intern\data\sample_jds.csv"
$csvData = Import-Csv $jdFile
$jdIDs = $csvData.id

if ($mode -eq "one") {
    $jdInput = Read-Host "Enter JD ID (e.g., JD_1, JD_2)"
    $jdIDs = @($jdInput)
}

foreach ($jd in $jdIDs) {
    try {
        # Get top 5 candidates for the JD
        $candidates = Invoke-RestMethod -Uri "http://127.0.0.1:5000/top_candidates?jd_id=$jd&top_n=5" -Method GET

        if (-not $candidates) {
            Write-Host "No candidates found for $jd" -ForegroundColor Yellow
            continue
        }

        Write-Host "`n--- Top 5 Candidates for $jd ---" -ForegroundColor Cyan

        # Display top 5 with color coding
        foreach ($cand in $candidates) {
            $status = if ($cand.location_match -eq $true) { "[HIRE]" } else { "[REJECT]" }
            $color = if ($status -eq "[HIRE]") { "Green" } else { "Red" }
            Write-Host "$status $($cand.cv_name) | Score: $($cand.score) | Skills: $($cand.skill_overlap) | Location: $($cand.location_match)" -ForegroundColor $color
            Write-Host "    JD ID: $($cand.jd_id)"
            Write-Host "    JD Title: $($cand.jd_title)"
            Write-Host "    Candidate ID: $($cand.cv_id)"
            Write-Host "    Rank: $($cand.rank)"
            Write-Host "    Resume Snippet: $($cand.resume_snippet)`n"
        }

        # Pick the top hire (highest score with location match = true)
        $hireCandidate = $candidates |
            Where-Object { $_.location_match -eq $true } |
            Sort-Object score -Descending |
            Select-Object -First 1

        if ($hireCandidate) {
            Write-Host "`n--- Hired Candidate for $jd ---" -ForegroundColor Green
            Write-Host "[HIRE] $($hireCandidate.cv_name) | Score: $($hireCandidate.score) | Skills: $($hireCandidate.skill_overlap) | Location: $($hireCandidate.location_match)" -ForegroundColor Green
            Write-Host "    JD ID: $($hireCandidate.jd_id)"
            Write-Host "    JD Title: $($hireCandidate.jd_title)"
            Write-Host "    Candidate ID: $($hireCandidate.cv_id)"
            Write-Host "    Rank: $($hireCandidate.rank)"
            Write-Host "    Resume Snippet: $($hireCandidate.resume_snippet)`n"

            # Save only hired candidate to CSV
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $outputFile = "C:\Task_Aiml_Intern\data\hired_${jd}_$timestamp.csv"
            $hireCandidate | Export-Csv -Path $outputFile -NoTypeInformation
            Write-Host "Hired candidate saved to $outputFile" -ForegroundColor Green
        } else {
            Write-Host "No suitable hire found for $jd" -ForegroundColor Yellow
        }

    } catch {
        Write-Host "Error fetching data for $jd -> $($_.Exception.Message)" -ForegroundColor Red
    }
}
