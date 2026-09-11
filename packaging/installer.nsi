; Windows installer betigi — F6-007
;
; Kabul: Uygulama, kisayol ve kaldirma girdisi beklenen konumdadir.
;
; Uc sey kurulur ve ucu de F6-008'de geri okunarak dogrulanir:
;   1. uygulama dosyalari  -> $INSTDIR
;   2. baslat menusu kisayolu -> $SMPROGRAMS
;   3. kaldirma girdisi    -> Uninstall kayit defteri anahtari
;
; Kurulum KULLANICI BAZINDA yapilir (HKCU + LOCALAPPDATA): yonetici hakki
; istemez. Yonetici gerektiren bir kurulum, kullanicinin kendi
; makinesinde deneyemedigi bir kurulumdur; dagitim kabulunu zorlastirir.
;
; Surum ve kaynak dizin disaridan verilir; boylece VERSION dosyasi tek
; dogruluk kaynagi olarak kalir:
;
;   makensis /DAPP_VERSION=<surum> /DSOURCE_DIR=... /DOUT_FILE=... installer.nsi

!ifndef APP_VERSION
  !error "APP_VERSION verilmedi (VERSION dosyasindan gelmeli)"
!endif
!ifndef SOURCE_DIR
  !error "SOURCE_DIR verilmedi (paketlenmis klasor)"
!endif
!ifndef OUT_FILE
  !error "OUT_FILE verilmedi"
!endif

!define APP_NAME "SONAR Veri Analiz Panosu"
!define APP_EXE "sonar-analyzer.exe"
!define APP_KEY "SonarAnalyzer"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_KEY}"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${OUT_FILE}"
Unicode True
RequestExecutionLevel user
InstallDir "$LOCALAPPDATA\Programs\${APP_KEY}"
InstallDirRegKey HKCU "Software\${APP_KEY}" "InstallDir"
SetCompressor /SOLID lzma

ShowInstDetails show
ShowUninstDetails show

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Uygulama" SecApp
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; Paketlenmis klasorun TAMAMI kopyalanir: PyInstaller onedir duzeninde
  ; _internal altindaki her sey gerekli.
  File /r "${SOURCE_DIR}\*.*"

  ; Kisayol: baslat menusu.
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"

  ; Kaldirici ve kaldirma girdisi.
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\${APP_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  ; Yalniz KURULUMUN getirdikleri silinir. Kullanicinin workspace ve kayit
  ; dosyalari $INSTDIR disindadir ve bu yuzden RMDir /r guvenlidir;
  ; F6-008 bunu ayrica dogrular.
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  Delete "$INSTDIR\uninstall.exe"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\${APP_EXE}"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "Software\${APP_KEY}"
SectionEnd
