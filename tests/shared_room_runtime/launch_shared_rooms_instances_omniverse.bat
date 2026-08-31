@echo off
setlocal

set "KIT_REPOSITORY=%~d0\omniverse_kit_app"
set "FIXTURE_ROOT=%~dp0"
set "EXTENSION_ROOT=%FIXTURE_ROOT%kit_exts"
set "STAGE_PATH=%FIXTURE_ROOT%test_room_map_shared_rooms_instances.usda"
set "STAGE_PATH_FOR_KIT=%STAGE_PATH:\=/%"

if not exist "%KIT_REPOSITORY%\repo.bat" (
    echo [ORMS] Kit launcher not found: %KIT_REPOSITORY%\repo.bat
    exit /b 1
)

if not exist "%STAGE_PATH%" (
    echo [ORMS] Validation scene not found: %STAGE_PATH%
    exit /b 1
)

if not exist "%EXTENSION_ROOT%\msp.orms.fixture_launcher\config\extension.toml" (
    echo [ORMS] Fixture launcher extension is missing.
    exit /b 1
)

pushd "%KIT_REPOSITORY%"
call ".\repo.bat" launch -n msp.case03.blackwell.kit -- --ext-folder "%EXTENSION_ROOT%" --enable msp.orms.fixture_launcher --/app/content/emptyStageOnStart=true "--/exts/omni.kit.window.script_editor/snippetFolders/0=${kit}/snippets" "--/exts/omni.kit.window.script_editor/snippetFolders/1=${kit}/snippets" "--/exts/msp.orms.fixture_launcher/stagePath=%STAGE_PATH_FOR_KIT%"
set "LAUNCH_EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %LAUNCH_EXIT_CODE%
