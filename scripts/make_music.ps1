# Generate 3 royalty-free cinematic ambient tracks for the 48 Laws of Power Reels.
# Each track is ~30s of dark, sustained, minor-key drone built from layered sine waves
# with tremolo, reverb-style echo, lowpass filtering, and fades.
# Output: e:\instaautomatic\music\*.mp3
$ErrorActionPreference = "Stop"
$outDir = "e:\instaautomatic\music"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# Each track: (name, [freqHz triples], tremolo Hz, echo delay ms)
$tracks = @(
  @{ name="01_iron_resolve.mp3";   freqs=@(55.00, 82.50, 110.00, 164.81); tremolo=0.25; echo=1800; key="A minor: A1, E2, A2, E3" },
  @{ name="02_the_strategist.mp3"; freqs=@(73.42, 110.00, 146.83, 220.00); tremolo=0.35; echo=1400; key="D minor: D2, A2, D3, A3" },
  @{ name="03_throne_of_power.mp3";freqs=@(41.20, 61.74, 82.41, 123.47);   tremolo=0.18; echo=2200; key="E minor: E1, B1, E2, B2" }
)
$dur = 30

foreach ($t in $tracks) {
  $inputs = @()
  $vols = @()
  $i = 0
  foreach ($f in $t.freqs) {
    $inputs += "-f","lavfi","-i","sine=f=$f`:d=$dur"
    # progressively quieter for higher harmonics, plus subtle detune-feel
    $v = [math]::Round(0.55 - 0.10 * $i, 2)
    $vols += "[$i]volume=$v[a$i]"
    $i++
  }
  $mixIn = (0..($t.freqs.Count-1) | ForEach-Object { "[a$_]" }) -join ""
  $n = $t.freqs.Count
  $tr = $t.tremolo
  $ec = $t.echo
  $fadeOutSt = $dur - 4
  $filter = ($vols -join ";") + ";" + $mixIn + "amix=inputs=$n" + ":duration=longest:normalize=0," + `
            "tremolo=f=$tr" + ":d=0.4," + `
            "aecho=0.8:0.85:$ec" + ":0.45," + `
            "highpass=f=30," + `
            "lowpass=f=1800," + `
            "volume=0.75," + `
            "afade=t=in:d=2.5," + `
            "afade=t=out:d=4:st=$fadeOutSt"
  $out = Join-Path $outDir $t.name
  Write-Host "Generating $($t.name) ($($t.key))..."
  $args = @($inputs) + @("-filter_complex", $filter, "-ac", "2", "-ar", "44100", "-b:a", "192k", "-y", $out)
  & ffmpeg -loglevel error @args
  if (Test-Path $out) { "  -> $out  $((Get-Item $out).Length) bytes" } else { "  FAILED" }
}
