; Inno Setup 6 script for TBAS Sync. Built by buildRelease.ps1 after the zip:
;   ISCC /DAppVersionNum=17 /DAppVersionLabel=v1.7 installer\TBASSync.iss
; Output: release\TBASSync-Setup.exe
;
; Per-user install (no admin prompt), so the app can replace its own exe when it
; updates itself. Settings in %APPDATA%\TBASSync are never touched.
;
; AppId, AppName, AppMutex and RunValueName can be overridden with /D so a test
; build can't collide with a real install.

#ifndef AppId
  #define AppId "TBASSync-6B0F3C2E-8D4A-4F7B-9E21-5A7C3D9B1E64"
#endif
#ifndef AppName
  #define AppName "TBAS Sync"
#endif
; Held by main.py while the app runs. Pass /DAppMutex= (empty) to disable.
#ifndef AppMutex
  #define AppMutex "Local\TBASSync"
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
#if AppMutex != ""
AppMutex={#AppMutex}
#endif
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
WizardStyle=modern
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

{ Remove the "start with Windows" entry only if it points into this install
  folder: a member may also run another copy from somewhere else. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Value, Prefix: String;
begin
  if CurUninstallStep <> usUninstall then
    Exit;
  if not RegQueryStringValue(HKCU, RunKey, '{#RunValueName}', Value) then
    Exit;
  Value := Lowercase(Value);
  if (Length(Value) > 0) and (Value[1] = '"') then
    Delete(Value, 1, 1);
  Prefix := Lowercase(AddBackslash(ExpandConstant('{app}')));
  if Pos(Prefix, Value) = 1 then
    RegDeleteValue(HKCU, RunKey, '{#RunValueName}');
end;
