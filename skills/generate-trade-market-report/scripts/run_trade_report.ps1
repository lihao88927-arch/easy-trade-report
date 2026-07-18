[CmdletBinding(DefaultParameterSetName = 'Live')]
param(
    [Parameter(Mandatory = $true)]
    [string]$Country,

    [string[]]$HsCodes = @('8504', '8535', '8536', '8537'),

    [int]$EndYear = ((Get-Date).Year - 1),

    [ValidateRange(2, 30)]
    [int]$Years = 5,

    [ValidateRange(1, 100)]
    [int]$Top = 10,

    [Parameter(Mandatory = $true)]
    [string]$Output,

    [Parameter(ParameterSetName = 'Offline', Mandatory = $true)]
    [string]$InputCsv,

    [Parameter(ParameterSetName = 'Live')]
    [string]$RawCsv,

    [string]$SourceLabel,

    [string]$EngineRoot
)

$ErrorActionPreference = 'Stop'

function Test-TradeReportPython {
    param([Parameter(Mandatory = $true)][string]$Executable)

    & $Executable -c "import easy_trade_report" 2>$null
    return $LASTEXITCODE -eq 0
}

$candidates = [System.Collections.Generic.List[string]]::new()
if ($EngineRoot) {
    $resolvedRoot = (Resolve-Path -LiteralPath $EngineRoot -ErrorAction Stop).Path
    $candidates.Add((Join-Path $resolvedRoot '.venv\Scripts\python.exe'))
    $candidates.Add((Join-Path $resolvedRoot 'work\.venv\Scripts\python.exe'))
    $candidates.Add((Join-Path $resolvedRoot '.venv\bin\python'))
    $candidates.Add((Join-Path $resolvedRoot 'work\.venv\bin\python'))
}

foreach ($commandName in @('python', 'py')) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
        $candidates.Add($command.Source)
    }
}

$python = $null
foreach ($candidate in $candidates | Select-Object -Unique) {
    if ((Test-Path -LiteralPath $candidate) -and (Test-TradeReportPython -Executable $candidate)) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    throw "Easy Trade Report is not installed in a discoverable Python environment. Install the repository with: python -m pip install -e .  For XLSX input also install: python -m pip install -e '.[excel]'"
}

$arguments = @(
    '-m', 'easy_trade_report.cli',
    '--country', $Country,
    '--hs'
) + $HsCodes + @(
    '--end-year', [string]$EndYear,
    '--years', [string]$Years,
    '--top', [string]$Top,
    '--output', $Output
)

if ($PSCmdlet.ParameterSetName -eq 'Offline') {
    if (-not (Test-Path -LiteralPath $InputCsv)) {
        throw "Input CSV not found: $InputCsv"
    }
    $arguments += @('--input-csv', $InputCsv)
}
elseif ($RawCsv) {
    $arguments += @('--raw-csv', $RawCsv)
}

if ($SourceLabel) {
    $arguments += @('--source-label', $SourceLabel)
}

& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Trade report engine exited with code $LASTEXITCODE"
}

Get-Item -LiteralPath $Output
