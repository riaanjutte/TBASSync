; Inno Setup 6 script for TBAS Sync. Built by buildRelease.ps1 after the zip:
;   ISCC /DAppVersionNum=17 /DAppVersionLabel=v1.7 installer\TBASSync.iss
; Output: release\TBASSync-Setup.exe
;
; Per-user install (no admin prompt), so the app can replace its own exe when it
; updates itself. Settings in %APPDATA%\TBASSync are never touched.
;
; Setup closes a running TBAS Sync itself, wherever its exe is, and so does the
; uninstaller once you confirm. The wizard uses the app's dark theme and logo:
; wizard-large.png and wizard-small.png are made from Resources\TBAS.png.
;
; AppId, AppName, AppMutex, AppExeOriginalName and RunValueName can be overridden
; with /D so a test build can't collide with a real install or close the real app.

#if Ver < EncodeVer(6, 7, 0)
  #error Inno Setup 6.7.0 or later is needed (WizardBackColor, PNG wizard images)
#endif

#ifndef AppId
  #define AppId "TBASSync-6B0F3C2E-8D4A-4F7B-9E21-5A7C3D9B1E64"
#endif
#ifndef AppName
  #define AppName "TBAS Sync"
#endif
; Held by main.py while the app runs.
#ifndef AppMutex
  #define AppMutex "Local\TBASSync"
#endif
; OriginalFilename in the app exe's version info (versionFileTemplate.txt): it
; identifies a running copy even when the download was renamed "TBASSync(2).exe".
#ifndef AppExeOriginalName
  #define AppExeOriginalName "TBASSync.exe"
#endif
; Written by Services/autostartService.py under HKCU\...\Run.
#ifndef RunValueName
  #define RunValueName "TBASSync"
#endif
#ifndef AppVersionNum
  #error Pass the version: /DAppVersionNum=17 /DAppVersionLabel=v1.7
#endif
#ifndef AppVersionLabel
  #error Pass the version: /DAppVersionNum=17 /DAppVersionLabel=v1.7
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersionLabel}
VersionInfoVersion={#AppVersionNum}
AppPublisher=TBAS
AppPublisherURL=https://github.com/riaanjutte/TBASSync
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
; the app's colours (GUI/customTheme.py): BG_DARK behind the pages
WizardStyle=modern dark hidebevels
WizardBackColor=#1c1c1c
WizardImageFile=wizard-large.png
WizardSmallImageFile=wizard-small.png
WizardSmallImageBackColor=none
SetupIconFile=..\Resources\TBAS.ico
UninstallDisplayIcon={app}\TBASSync.exe
UninstallDisplayName={#AppName}
OutputDir=..\release
OutputBaseFilename=TBASSync-Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; No ignoreversion: an older Setup won't downgrade an exe that has updated itself.
Source: "..\release\TBASSync.exe"; DestDir: "{app}"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\TBASSync.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\TBASSync.exe"; Tasks: desktopicon

[Run]
; skipifsilent: a silent install must never start the app.
Filename: "{app}\TBASSync.exe"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';

{ PowerShell that force-closes every running copy of the app and exits with the
  number still running. The app is two processes: PyInstaller's launcher and,
  as its child, the app itself. Stopping the child first lets the launcher exit
  on its own and delete the app's unpacked files from %TEMP%. }
function CloseScript(): String;
begin
  Result :=
    '$n = ''{#AppExeOriginalName}''; ' +
    'function Find { @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and ' +
      '(Get-Item -LiteralPath $_.ExecutablePath -ErrorAction SilentlyContinue).VersionInfo.OriginalFilename -eq $n }) }; ' +
    '$all = Find; $ids = @($all | ForEach-Object { $_.ProcessId }); ' +
    '$inner = @($all | Where-Object { $ids -contains $_.ParentProcessId }); ' +
    '$outer = @($all | Where-Object { $ids -notcontains $_.ParentProcessId } | ForEach-Object { $_.ProcessId }); ' +
    'foreach ($p in $inner) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }; ' +
    'if ($inner.Count -and $outer.Count) { Wait-Process -Id $outer -Timeout 10 -ErrorAction SilentlyContinue }; ' +
    '$left = Find; foreach ($p in $left) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }; ' +
    'if ($left.Count) { Wait-Process -Id ($left | ForEach-Object { $_.ProcessId }) -Timeout 5 -ErrorAction SilentlyContinue }; ' +
    'exit (Find).Count';
end;

{ Close the app wherever its exe is: an old zip copy would otherwise keep running
  and keep starting with Windows. True when no copy is left running. If
  PowerShell can't tell, the app's mutex decides. }
function CloseRunningApp(): Boolean;
var
  ResultCode: Integer;
begin
  Result := (Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
                  '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "' + CloseScript() + '"',
                  '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0))
            or not CheckForMutexes('{#AppMutex}');
  Log(Format('Closing {#AppName}: PowerShell exit code %d, closed: %d', [ResultCode, Ord(Result)]));
end;

{ After the user clicks Install, before any file is copied. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if not CloseRunningApp() then
    Result := '{#AppName} is still running and could not be closed. Quit it from its tray icon ' +
              '(right-click > Quit), then click Back and Install again.';
end;

{ After the user confirms the uninstall: close the app, so its exe can be deleted.
  Then remove the "start with Windows" entry only if it points into this install
  folder: a member may also run another copy from somewhere else. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Value, Prefix: String;
begin
  if CurUninstallStep <> usUninstall then
    Exit;
  CloseRunningApp();
  if not RegQueryStringValue(HKCU, RunKey, '{#RunValueName}', Value) then
    Exit;
  Value := Lowercase(Value);
  if (Length(Value) > 0) and (Value[1] = '"') then
    Delete(Value, 1, 1);
  Prefix := Lowercase(AddBackslash(ExpandConstant('{app}')));
  if Pos(Prefix, Value) = 1 then
    RegDeleteValue(HKCU, RunKey, '{#RunValueName}');
end;
