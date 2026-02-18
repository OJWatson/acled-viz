@ECHO OFF

pushd %~dp0

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=uv run python build_docs.py
)
set SOURCEDIR=.
set BUILDDIR=_build

if "%1" == "" goto help

if "%1"=="html" (
	%SPHINXBUILD%
	goto end
)
echo Unsupported target: %1
exit /b 2
goto end

:help
echo Supported target: html

:end
popd
