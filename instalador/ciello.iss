; Instalador do Ciello OS (Inno Setup 6). Gera CielloOS-Setup-<versão>.exe.
; Quem compila é o GitHub Actions (.github/workflows/instalador.yml). Para compilar no PC:
;   git archive --format=zip HEAD -o app.zip  e extraia em build\app  (só os arquivos do repositório)
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DVersao=1.0.1 /DFonte=..\build\app instalador\ciello.iss
; O instalador copia o programa para a pasta escolhida e roda instalador\preparar.ps1 escondido (sem janela de CMD nem
; de Python): o andamento de cada etapa aparece na própria tela do instalador. Se o .venv (de onde sai o pythonw.exe dos
; atalhos) não ficar de pé, ele mostra o motivo e oferece tentar de novo.

#if VER < EncodeVer(6, 3, 0)
  #error O instalador precisa do Inno Setup 6.3 ou mais novo (ExecAndLogOutput).
#endif

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Fonte
  #define Fonte "..\build\app"
#endif

[Setup]
AppId={{6B2C3F1E-7A3D-4C8B-9E21-C1E770C1E770}
AppName=Ciello OS
AppVersion={#Versao}
AppVerName=Ciello OS {#Versao}
AppPublisher=CIELLO
AppPublisherURL=https://github.com/MTCiello/AGENTE-DE-POSTAGEM
AppUpdatesURL=https://github.com/MTCiello/AGENTE-DE-POSTAGEM/releases
DefaultDirName={sd}\Ciello\CielloOS
DisableDirPage=no
UsePreviousAppDir=yes
DefaultGroupName=Ciello OS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\build
OutputBaseFilename=CielloOS-Setup-{#Versao}
SetupIconFile=marca\ciello.ico
UninstallDisplayIcon={app}\instalador\marca\ciello.ico
UninstallDisplayName=Ciello OS
WizardStyle=modern
WizardImageFile=marca\assistente.bmp
WizardSmallImageFile=marca\assistente-pequeno.bmp
WizardImageStretch=no
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Messages]
pt.WelcomeLabel2=Este assistente vai instalar o Ciello OS {#Versao} no seu computador: a área de trabalho com o escritório de agentes, Financeiro, Comercial, Conteúdo, Anúncios e os estúdios de Vídeo e Voz.%n%nNo fim ele baixa o que o assistente precisa (Python, FFmpeg, Node.js, Claude Code e as bibliotecas), mostrando o andamento aqui mesmo, sem abrir outras janelas. Deixe o computador ligado à internet.
pt.SelectDirDesc=Onde o Ciello OS vai ficar?
pt.SelectDirLabel3=O Ciello OS e os seus dados (leads, financeiro, rascunhos) ficam nesta pasta. Evite pastas sincronizadas como OneDrive.

[Types]
Name: "completa"; Description: "Completa (com o Estúdio de Voz, baixa uns 3 GB a mais)"
Name: "padrao"; Description: "Padrão"
Name: "personalizada"; Description: "Personalizada"; Flags: iscustom

[Components]
Name: "base"; Description: "Ciello OS (área de trabalho, escritório e agentes)"; Types: completa padrao personalizada; Flags: fixed
Name: "claude"; Description: "Claude Code (faz os agentes de IA trabalharem)"; Types: completa padrao
Name: "video"; Description: "Estúdio de Vídeo (Node.js, Remotion e HyperFrames)"; Types: completa padrao
Name: "voz"; Description: "Estúdio de Voz (Kokoro, Chatterbox e Whisper · uns 3 GB)"; Types: completa

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Atalhos:"
Name: "rotinas"; Description: "Rodar sozinho, sem abrir janela: o Bom dia às 7h e o piloto da rede social de hora em hora"; GroupDescription: "Rotinas automáticas (dá para mudar depois no Ciello OS, em Rede social):"; Flags: unchecked

[Files]
Source: "{#Fonte}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; atalhos .cmd das versões antigas: agora tudo abre pelo ícone, sem janela de CMD
Type: files; Name: "{app}\Ciello.cmd"
Type: files; Name: "{app}\instalar.cmd"
Type: files; Name: "{app}\testar.cmd"
Type: files; Name: "{app}\agendar.cmd"

[Dirs]
Name: "{app}\estado"

[Icons]
Name: "{autoprograms}\Ciello OS\Ciello OS"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\instalador\lancador.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\instalador\marca\ciello.ico"; Comment: "Abrir o Ciello OS"
Name: "{autoprograms}\Ciello OS\Atualizações do Ciello OS"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\instalador\atualizador.pyw"" --procurar"; WorkingDir: "{app}"; IconFilename: "{app}\instalador\marca\ciello.ico"; Comment: "Procurar e instalar versões novas"
Name: "{autoprograms}\Ciello OS\Reinstalar dependências"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\instalador\atualizador.pyw"" --reparar"; WorkingDir: "{app}"; IconFilename: "{app}\instalador\marca\ciello.ico"; Comment: "Baixar de novo o que o Ciello OS precisa, sem janela de CMD"
Name: "{autoprograms}\Ciello OS\Desinstalar o Ciello OS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Ciello OS"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\instalador\lancador.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\instalador\marca\ciello.ico"; Comment: "Abrir o Ciello OS"; Tasks: desktopicon

[Run]
; as dependências rodam no [Code] (Preparar), que confere o resultado; aqui só o "Abrir agora"
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\instalador\lancador.pyw"""; WorkingDir: "{app}"; Description: "Abrir o Ciello OS agora"; Flags: postinstall nowait skipifsilent; Check: VenvPronto

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""Ciello Bom Dia"""; Flags: runhidden; RunOnceId: "RotinaBomDia"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""Ciello Piloto"""; Flags: runhidden; RunOnceId: "RotinaPiloto"

[UninstallDelete]
; o que o instalador baixou depois; os seus dados (estado, comercial, financeiro, founder, audio) ficam na pasta
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\reels\node_modules"
Type: filesandordirs; Name: "{app}\ferramentas"
Type: filesandordirs; Name: "{app}\comercial\bin"

[Code]
function OpcoesPreparar(Param: String): String;
begin
  Result := '';
  if WizardIsComponentSelected('voz') then Result := Result + ' -Voz';
  if not WizardIsComponentSelected('video') then Result := Result + ' -SemVideo';
  if not WizardIsComponentSelected('claude') then Result := Result + ' -SemClaude';
end;

function VenvPronto: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\.venv\Scripts\pythonw.exe'));
end;

function MotivoPreparar(Codigo: Integer): String;
begin
  case Codigo of
    1: Result := 'O Python 3.12 não instalou. Confira a internet ou instale pelo site python.org.';
    2: Result := 'O ambiente Python (.venv) não foi criado. Pastas no OneDrive e alguns antivírus atrapalham: prefira C:\Ciello\CielloOS.';
    -1: Result := 'O Windows não deixou abrir o PowerShell.';
  else
    Result := 'A preparação parou no meio (código ' + IntToStr(Codigo) + ').';
  end;
end;

var
  Pagina: TOutputProgressWizardPage;

function NomeEtapa(Chave: String): String;
begin
  if Chave = 'python' then Result := 'Instalando o Python 3.12'
  else if Chave = 'venv' then Result := 'Criando o ambiente do Ciello OS'
  else if Chave = 'bibliotecas' then Result := 'Baixando as bibliotecas do Python'
  else if Chave = 'git' then Result := 'Instalando o Git'
  else if Chave = 'ffmpeg' then Result := 'Instalando o FFmpeg (áudio e vídeo)'
  else if Chave = 'node' then Result := 'Instalando o Node.js (gerador de vídeo)'
  else if Chave = 'claude' then Result := 'Instalando o Claude Code (os agentes de IA)'
  else if Chave = 'sdr' then Result := 'Baixando o buscador do Google Maps (SDR)'
  else if Chave = 'video' then Result := 'Preparando o Estúdio de Vídeo (Remotion e HyperFrames)'
  else if Chave = 'voz' then Result := 'Preparando o Estúdio de Voz (uns 3 GB, demora mais)'
  else if Chave = 'conferir' then Result := 'Conferindo se ficou tudo certo'
  else Result := 'Preparando o seu computador';
end;

{ Cada linha que o preparar.ps1 escreve chega aqui: "@@ETAPA <n> <chave> ..." muda a etapa e a barra; o resto aparece
  embaixo, pequeno, para mostrar que está andando. }
procedure LinhaPreparar(const S: String; const Error, FirstLine: Boolean);
var
  Resto, Chave: String;
  N, P: Integer;
begin
  if Copy(S, 1, 8) = '@@ETAPA ' then
  begin
    Resto := Copy(S, 9, Length(S));
    P := Pos(' ', Resto);
    N := StrToIntDef(Copy(Resto, 1, P - 1), 0);
    Resto := Copy(Resto, P + 1, Length(Resto));
    P := Pos(' ', Resto);
    if P > 0 then Chave := Copy(Resto, 1, P - 1) else Chave := Resto;
    Pagina.SetText(NomeEtapa(Chave) + '...', '');
    Pagina.SetProgress(N - 1, 11);
  end
  else if Trim(S) <> '' then
  begin
    if Length(S) > 110 then
      Pagina.Msg2Label.Caption := Copy(Trim(S), 1, 107) + '...'
    else
      Pagina.Msg2Label.Caption := Trim(S);
  end;
end;

procedure LigarRotinas;
var
  Codigo: Integer;
begin
  if not WizardIsTaskSelected('rotinas') then Exit;
  Pagina.SetText('Ligando as rotinas automáticas...', '');
  Exec(ExpandConstant('{app}\.venv\Scripts\python.exe'), '"' + ExpandConstant('{app}\instalador\rotinas.pyw') + '" ligar',
       ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Codigo);
end;

procedure Preparar;
var
  Codigo: Integer;
  Params: String;
begin
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\instalador\preparar.ps1') +
            '" -Pasta "' + ExpandConstant('{app}') + '" -SemPausa' + OpcoesPreparar('');
  Pagina := CreateOutputProgressPage('Preparando o seu computador',
    'O instalador está baixando o que o Ciello OS precisa. Pode levar de 10 a 30 minutos na primeira vez; não precisa fazer nada.');
  Pagina.Show;
  try
    repeat
      Pagina.SetText('Começando...', '');
      Pagina.SetProgress(0, 11);
      if not ExecAndLogOutput('powershell.exe', Params, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Codigo, @LinhaPreparar) then
        Codigo := -1;
      if VenvPronto then
      begin
        Pagina.SetProgress(11, 11);
        LigarRotinas;
        Exit;
      end;
    until MsgBox('Não deu para terminar a preparação do Ciello OS.' + #13#10#13#10 + MotivoPreparar(Codigo) + #13#10#13#10 +
                 'Tentar de novo agora?', mbError, MB_RETRYCANCEL) <> IDRETRY;
  finally
    Pagina.Hide;
  end;
  MsgBox('O Ciello OS foi copiado, mas ainda falta preparar o Python.' + #13#10 +
         'Quando quiser, rode este instalador de novo (ele mantém os seus dados).' + #13#10#13#10 +
         'O que aconteceu fica anotado em ' + ExpandConstant('{app}\estado\instalacao.log'), mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    Preparar;
end;
