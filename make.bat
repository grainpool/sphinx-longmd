@ECHO OFF
set SPHINXBUILD=sphinx-build
set SOURCEDIR=source
set BUILDDIR=_build

if "%1"=="clean" (
    rmdir /s /q %BUILDDIR%
    goto end
)

%SPHINXBUILD% -b html %SOURCEDIR% %BUILDDIR%/html

:end
