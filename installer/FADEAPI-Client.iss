; FADEAPI-Client Inno Setup Script

#define MyAppName "FADEAPI-Client"
#define MyAppPublisher "FAdeA"
#define MyAppURL "https://github.com/marzzelo/FAdeAPI-client"
#define MyAppExeName "FADEAPI-Client.exe"

; La versión se sobreescribe desde línea de comandos con /DAppVersion=x.y.z
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{C4D84B37-8E3C-4B1F-9A12-FADEAPI-CLIENT}} 
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=yes
OutputBaseFilename={#MyAppName}_Setup_{#AppVersion}_win64
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copia todo el onedir de PyInstaller dentro de {app}
Source: "..\dist\FADEAPI-Client\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
